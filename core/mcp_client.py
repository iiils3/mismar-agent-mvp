from __future__ import annotations
import ipaddress,json,socket
from urllib.parse import urlparse
from urllib.request import Request,urlopen
def _public_url(url):
    p=urlparse(url)
    if p.scheme not in {"http","https"} or not p.hostname: raise ValueError("MCP الرابط يجب أن يكون http أو https")
    try:
        infos=socket.getaddrinfo(p.hostname,p.port or (443 if p.scheme=="https" else 80),type=socket.SOCK_STREAM)
        for info in infos:
            ip=ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast: raise ValueError("هذا العنوان يشير إلى شبكة داخلية وغير مسموح به")
    except socket.gaierror as exc: raise ValueError("تعذر حل عنوان MCP") from exc
    return url
def _call(url,method,params,token=""):
    headers={"Content-Type":"application/json","Accept":"application/json, text/event-stream","MCP-Protocol-Version":"2026-07-28","Mcp-Method":method}
    if token: headers["Authorization"]=token if token.lower().startswith("bearer ") else "Bearer "+token
    if method=="tools/list": headers["Mcp-Name"]="tools"
    elif method=="server/discover": headers["Mcp-Name"]="server"
    req=Request(_public_url(url),data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),headers=headers,method="POST")
    with urlopen(req,timeout=12) as response: raw=response.read().decode("utf-8","replace")
    if raw.startswith("data:"): raw=next((line[5:].strip() for line in raw.splitlines() if line.startswith("data:")),"{}")
    return json.loads(raw)
def discover_tools(url,token=""):
    try: result=_call(_public_url(url),"tools/list",{},token)
    except Exception: result=_call(_public_url(url),"server/discover",{},token)
    data=result.get("result",result); tools=data.get("tools",[]) if isinstance(data,dict) else []
    return {"ok":True,"name":data.get("serverInfo",{}).get("name") if isinstance(data,dict) else None,"tools":[{"name":t.get("name"),"description":t.get("description",""),"inputSchema":t.get("inputSchema",{})} for t in tools[:100]]}
