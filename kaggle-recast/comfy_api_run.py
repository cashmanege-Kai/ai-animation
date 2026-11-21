"""Submit an explicitly exported ComfyUI API workflow on localhost, and copy finished outputs."""
import argparse,json,time,urllib.request,uuid,shutil
from pathlib import Path

def request(base,path,payload=None):
    data=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request(base+path,data=data,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)

def run(api_file,base,output_root,export_dir,timeout):
    graph=json.loads(Path(api_file).read_text(encoding='utf8'))
    if 'nodes' in graph or 'definitions' in graph:raise ValueError('This is UI JSON. Export API format in ComfyUI after selecting the correct person mask.')
    if not graph or not all(isinstance(v,dict) and 'class_type' in v and 'inputs' in v for v in graph.values()):raise ValueError('Invalid API node graph')
    available=request(base,'/object_info');missing=sorted(set(n['class_type'] for n in graph.values())-set(available))
    if missing:raise ValueError('Missing nodes: '+', '.join(missing))
    response=request(base,'/prompt',{'prompt':graph,'client_id':str(uuid.uuid4())})
    if 'prompt_id' not in response:raise RuntimeError(response)
    pid=response['prompt_id'];print('Submitted',pid,flush=True);deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        history=request(base,'/history/'+pid)
        if pid in history:
            result=history[pid];dest=Path(export_dir);dest.mkdir(parents=True,exist_ok=True)
            (dest/'comfy-history.json').write_text(json.dumps(result,indent=2),encoding='utf8')
            if result.get('status',{}).get('status_str')=='error':raise RuntimeError('Generation failed. See comfy-history.json; no automatic retry.')
            root=Path(output_root).resolve();copied=[]
            for node in result.get('outputs',{}).values():
                for values in node.values():
                    if not isinstance(values,list):continue
                    for v in values:
                        if not isinstance(v,dict) or 'filename' not in v or v.get('type','output')!='output':continue
                        path=(root/v.get('subfolder','')/v['filename']).resolve()
                        if not path.is_relative_to(root):raise ValueError('Output path escaped ComfyUI output folder')
                        if path.is_file():
                            target=dest/(pid[:8]+'-'+path.name);shutil.copyfile(path,target);copied.append(str(target))
            if not copied:raise RuntimeError('Run ended without a saved output. Ensure a video output node is connected.')
            print(json.dumps(copied,indent=2));return copied
        time.sleep(3)
    raise TimeoutError('Stopped polling; the submitted GPU job may still be running. Inspect queue before retrying.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('api_file');p.add_argument('--base',default='http://127.0.0.1:8188');p.add_argument('--output-root',default='/kaggle/working/ComfyUI/output');p.add_argument('--exports',default='/kaggle/working/exports');p.add_argument('--timeout',type=int,default=3600);a=p.parse_args();run(a.api_file,a.base,a.output_root,a.exports,a.timeout)
