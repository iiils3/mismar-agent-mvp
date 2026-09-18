from __future__ import annotations
import json,os,re,subprocess,threading
from pathlib import Path
from litellm import completion
from .base import BuildRequest,BuildResult,changed_files,worktree_ok

_lock=threading.Lock(); _cursor=0
def _keys():
    raw=os.getenv('MISMAR_CODING_API_KEYS','').strip()
    if raw: return [x.strip() for x in raw.split(',') if x.strip()]
    key=os.getenv('MISMAR_CODING_API_KEY','').strip()
    return [key] if key else []
def _model(): return os.getenv('MISMAR_CODING_MODEL') or os.getenv('MISMAR_MODEL') or 'openai/gpt-4o-mini'
def _complete(messages,max_tokens):
    keys=_keys()
    if not keys: raise RuntimeError('لا يوجد مفتاح Coding Worker مضبوط.')
    global _cursor
    with _lock: start=_cursor; _cursor=(_cursor+1)%len(keys)
    last=None
    for i in range(len(keys)):
        key=keys[(start+i)%len(keys)]
        try:
            r=completion(model=_model(),messages=messages,temperature=0,max_tokens=max_tokens,api_key=key)
            return r.choices[0].message.content or ''
        except Exception as exc:
            last=exc
            if not any(s in str(exc).lower() for s in ('429','rate','quota','timeout','temporar','503','502','500')): raise
    raise RuntimeError(f'كل مفاتيح البرمجة فشلت: {type(last).__name__}')
def _run(cmd,cwd,timeout=300):
    p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=timeout,check=False)
    return p.returncode,(p.stdout+'\n'+p.stderr)[-6000:]
def _files(repo):
    p=subprocess.run(['git','ls-files'],cwd=repo,text=True,capture_output=True,check=False)
    return [x for x in p.stdout.splitlines() if x and not x.startswith(('.git/','node_modules/','venv/'))][:1500]
def _read(repo,paths,limit=30000):
    chunks=[]; total=0
    for rel in paths:
        if not re.match(r'^[\w./-]+$',rel) or rel.startswith('../'): continue
        path=Path(repo,rel)
        if not path.is_file(): continue
        try: data=path.read_text(encoding='utf-8',errors='replace')
        except Exception: continue
        data=data[:10000]
        if total+len(data)>limit: data=data[:max(0,limit-total)]
        chunks.append(f'\n===== {rel} =====\n{data}')
        total+=len(data)
        if total>=limit: break
    return ''.join(chunks)
def _verify(repo):
    commands=[]
    if Path(repo,'pyproject.toml').exists() or Path(repo,'requirements.txt').exists(): commands.append(['python','-m','compileall','-q','.'])
    if Path(repo,'package.json').exists(): commands.append(['npm','run','build','--if-present'])
    if Path(repo,'pytest.ini').exists() or Path(repo,'tests').exists(): commands.append(['python','-m','pytest','-q'])
    if not commands: return True,'لا يوجد أمر تحقق قياسي؛ فحص Git فقط.'
    logs=[]
    for cmd in commands:
        code,out=_run(cmd,repo,600); logs.append('$ '+' '.join(cmd)+'\n'+out)
        if code: return False,'\n'.join(logs)
    return True,'\n'.join(logs)
class NativeCodingBuilder:
    name='native'
    def available(self): return bool(_keys())
    def _select_files(self,request,files):
        prompt=('Select at most 8 existing repository files needed for this task. Return ONLY a JSON array of paths. Never invent paths.\nTASK:\n'+request.task+'\nFILES:\n'+'\n'.join(files))
        raw=_complete([{'role':'user','content':prompt}],500)
        try: return [p for p in json.loads(raw) if p in files][:8]
        except Exception: return files[:8]
    def _patch(self,request,context,verify_error=''):
        prompt=('You are Mismar coding employee. Implement the task in the existing repo. Return ONLY a unified git diff that applies with git apply; no Markdown fences, commentary, or shell commands. Keep changes minimal. Do not modify CI permissions, secrets, auth boundaries, or unrelated files.\nTASK:\n'+request.task+'\nVERIFY_ERROR:\n'+verify_error[-5000:]+'\nCONTEXT:\n'+context)
        return _complete([{'role':'user','content':prompt}],2200).strip()
    def run(self,request):
        if not self.available(): return BuildResult(False,'Coding model key غير مضبوط.',[])
        if not worktree_ok(request.repo_path): return BuildResult(False,'المسار ليس مستودع Git.',[])
        files=_files(request.repo_path)
        try:
            selected=self._select_files(request,files); context=_read(request.repo_path,selected); last_error=''
            for attempt in range(max(1,request.max_attempts)):
                patch=self._patch(request,context,last_error).replace('```diff','').replace('```','').strip()
                if not patch.startswith('diff --git '): last_error='النموذج لم يرجع unified diff صالح.'; continue
                check,out=_run(['git','apply','--check','-'],request.repo_path)
                if check: last_error='git apply --check failed:\n'+out; continue
                check,out=_run(['git','apply','-'],request.repo_path)
                if check: last_error='git apply failed:\n'+out; continue
                ok,verify=_verify(request.repo_path)
                if ok: return BuildResult(True,f'تم التنفيذ بالـNative Coding Worker في المحاولة {attempt+1}.',changed_files(request.repo_path),verify)
                last_error=verify; context=_read(request.repo_path,selected)+'\n===== CURRENT DIFF =====\n'+_run(['git','diff','--','.'],request.repo_path)[1]
            return BuildResult(False,'فشل التحقق بعد محاولات الإصلاح.',changed_files(request.repo_path),last_error)
        except Exception as exc: return BuildResult(False,f'فشل Coding Worker: {type(exc).__name__}',changed_files(request.repo_path),str(exc)[-6000:])