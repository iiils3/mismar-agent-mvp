from __future__ import annotations
import json,os,queue,threading
from pathlib import Path
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse,StreamingResponse
from pydantic import BaseModel,Field
ROOT=Path(__file__).resolve().parent
app=FastAPI(title="Mismar AI Company OS"); MAX_PROMPT_CHARS=5000; MAX_ATTACHMENT_BYTES=20*1024*1024
class Attachment(BaseModel): name:str; type:str; size:int=Field(ge=0,le=MAX_ATTACHMENT_BYTES)
class CouncilRequest(BaseModel): request:str=Field(min_length=1,max_length=MAX_PROMPT_CHARS); mode:str="balanced"; attachments:list[Attachment]=Field(default_factory=list,max_length=10)
class MCPRequest(BaseModel): url:str; token:str=""
@app.get("/")
def home(): return FileResponse(ROOT/"web"/"index.html")
@app.get("/health")
def health(): return {"ok":True,"service":"mismar-agent-office","version":"2.0"}
@app.get("/api/status")
def status():
    keys=["OPENAI_API_KEY","GEMINI_API_KEY","GROQ_API_KEY","OPENROUTER_API_KEY","XAI_API_KEY"]
    return {"ok":True,"ai_configured":bool(os.getenv("MISMAR_MODEL") or os.getenv("MISMAR_SYNTHESIS_MODEL") or any(os.getenv(k) for k in keys)),"streaming":True,"mcp":True,"github_worker":bool(os.getenv("MISMAR_WORKER_URL"))}
def safe_error(exc):
    print(f"Mismar AI error: {type(exc).__name__}: {exc}",flush=True); return HTTPException(status_code=503,detail=f"AI engine unavailable: {type(exc).__name__}")
@app.post("/api/council")
def council(payload:CouncilRequest):
    try:
        from core.council import debate
        from core.synthesis import synthesize
        rounds={"fast":1,"balanced":2,"full":2,"deep":3}.get(payload.mode,2); result=debate(payload.request,payload.mode if payload.mode in ("full","deep") else "auto",rounds); decision=synthesize(payload.request,result)
        try: decision_json=json.loads(decision)
        except json.JSONDecodeError: decision_json={"decision":decision}
        return {"roles":result["roles"],"rounds":result["rounds"],"attachments":[a.model_dump() for a in payload.attachments],**decision_json}
    except Exception as exc: raise safe_error(exc)
def sse(data): return f"data: {json.dumps(data,ensure_ascii=False)}\n\n"
@app.post("/api/run")
def run_company(payload:CouncilRequest):
    q=queue.Queue()
    def emit(event): q.put(event)
    def worker():
        try:
            from core.council import debate
            from core.synthesis import synthesize
            rounds={"fast":1,"balanced":2,"full":2,"deep":3}.get(payload.mode,2)
            emit({"type":"system","stage":"فتح غرفة العمليات","message":"بدأت المهمة. راح تشوف التسليمات مرحلة بمرحلة.","done":True})
            result=debate(payload.request,payload.mode if payload.mode in ("full","deep") else "auto",rounds,on_event=emit)
            emit({"type":"system","stage":"Chief of Staff","message":"الرئيس يجمع النقاط المتفق عليها والتعارضات قبل القرار.","done":False}); decision=synthesize(payload.request,result)
            try: parsed=json.loads(decision); summary=parsed.get("decision",decision)
            except json.JSONDecodeError: summary=decision
            emit({"type":"system","stage":"القرار","message":"تم تجميع القرار التنفيذي.","summary":summary,"done":True})
            if os.getenv("MISMAR_WORKER_URL"):
                emit({"type":"system","stage":"المبرمج","message":"الرئيس سلّم القرار إلى محطة البرمجة. المبرمج سيعدل فرعاً منفصلاً ويشغل الفحوصات."})
                import urllib.request
                req=urllib.request.Request(os.getenv("MISMAR_WORKER_URL").rstrip("/")+"/build",data=json.dumps({"task":payload.request,"mode":payload.mode}).encode(),headers={"Content-Type":"application/json"},method="POST")
                try:
                    with urllib.request.urlopen(req,timeout=1200) as response: worker_result=json.loads(response.read().decode())
                    emit({"type":"github","message":"المبرمج أنهى التسليم إلى GitHub","detail":worker_result.get("pr_url") or worker_result.get("summary","تم التنفيذ"),"pr_url":worker_result.get("pr_url"),"branch":worker_result.get("branch")})
                except Exception as worker_exc:
                    emit({"type":"error","stage":"المبرمج / GitHub","message":f"فشل Worker: {type(worker_exc).__name__}"})
            else:
                emit({"type":"github","message":"مرحلة GitHub جاهزة للربط","detail":"نحتاج Worker مستقل ببيئة Git ثابتة حتى يكتب المبرمج ويشغل CI ويفتح PR بدون دمج تلقائي."})
            emit({"type":"done","message":"اكتملت غرفة العمليات."})
        except Exception as exc:
            print(f"Mismar run error: {type(exc).__name__}: {exc}",flush=True); q.put({"type":"error","stage":"خطأ","message":f"تعذر إكمال المهمة: {type(exc).__name__}"})
        finally: q.put(None)
    threading.Thread(target=worker,daemon=True).start()
    def stream():
        yield sse({"type":"system","stage":"اتصال","message":"تم فتح البث المباشر.","done":True})
        while True:
            item=q.get()
            if item is None: break
            yield sse(item)
    return StreamingResponse(stream(),media_type="text/event-stream",headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})
@app.post("/api/upload")
def upload_metadata(payload:list[Attachment]): return {"files":[item.model_dump() for item in payload[:10]]}
@app.post("/api/mcp/discover")
def mcp_discover(payload:MCPRequest):
    try:
        from core.mcp_client import discover_tools
        return discover_tools(payload.url,payload.token)
    except ValueError as exc: raise HTTPException(status_code=400,detail=str(exc))
    except Exception as exc:
        print(f"MCP error: {type(exc).__name__}: {exc}",flush=True); raise HTTPException(status_code=502,detail=f"MCP connection failed: {type(exc).__name__}")
