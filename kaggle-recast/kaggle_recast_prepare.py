"""Prepare a short silent input and patch an official ComfyUI UI workflow; never generate automatically."""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path

def prepare(source, character, workflow, comfy, start=0.0):
    source, character, workflow, comfy = map(Path, (source,character,workflow,comfy))
    for p in (source,character,workflow):
        if not p.is_file(): raise FileNotFoundError(p)
    target=comfy/'input'; target.mkdir(parents=True,exist_ok=True)
    video=target/'recast-source-77frames.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',str(start),'-i',str(source),'-an','-vf','scale=432:768:force_original_aspect_ratio=decrease,pad=432:768:(ow-iw)/2:(oh-ih)/2,fps=16','-frames:v','77','-c:v','libx264','-pix_fmt','yuv420p',str(video)],check=True)
    ref=target/'tennis-woman-reference.png'; shutil.copyfile(character,ref)
    data=json.loads(workflow.read_text(encoding='utf8'))
    for node in data.get('nodes',[]):
        if node['id']==145 and node['type']=='LoadVideo': node['widgets_values'][0]=video.name
        if node['id']==10 and node['type']=='LoadImage': node['widgets_values'][0]=ref.name
        if node['type']=='PixelPerfectResolution': node['widgets_values']=[432,768,'Just Resize']
        if node['id']==212 and node['type']=='ImageScale': node['widgets_values']=['lanczos',432,768,'center']
        if node['id']==21 and node['type']=='CLIPTextEncode':
            node['widgets_values']=['An adult woman with black ponytail in an ivory tennis polo, dark green pleated tennis skirt with opaque athletic shorts, white socks and court shoes. Preserve the original basketball motion, crowd, court, lighting and camera. Stable adult face, accurate hands, realistic fabric.']
    out=comfy/'user/default/workflows/tennis-recast-test-ui.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    # UI workflow has subgraphs and a manual mask editor: it is NOT /prompt API format.
    manifest={'mode':'Mix / character replacement','width':432,'height':768,'fps':16,'frames':77,'ui_workflow':str(out),'needs_manual_character_mask':True,'generation_submitted':False,'assets':[]}
    for p in (video,ref): manifest['assets'].append({'file':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    report=comfy.parent/'recast-preflight.json';report.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8');return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--character',required=True);p.add_argument('--workflow',required=True);p.add_argument('--comfy',required=True);p.add_argument('--start',type=float,default=0)
    a=p.parse_args();print(json.dumps(prepare(a.source,a.character,a.workflow,a.comfy,a.start),ensure_ascii=False,indent=2))
