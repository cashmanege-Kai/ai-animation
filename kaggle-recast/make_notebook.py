import json
from pathlib import Path
P=Path(__file__).parent
cells=[]
def md(s):cells.append({'cell_type':'markdown','metadata':{},'source':s.splitlines(True)})
def code(s):cells.append({'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':s.splitlines(True)})
md('''# Kaggle：網球服角色替換測試\n不是木偶上貼圖。使用官方 Wan2.2 Animate Mix 工作流程：參考圖＋動作影片＋人物遮罩。\n先測77幀、16fps、432×768，約4.8秒；成功後再分段處理16秒。\n**此Notebook不會自動生成、不建立公開連線，也不含模型或金鑰。** GPU不足時應停止；多張GPU的顯存不會自動合併。\nKaggle設定：私人Notebook，Internet開啟，Accelerator選GPU。把此套檔案和有權使用的來源影片加為Kaggle Input。\n''')
code('''from pathlib import Path
import subprocess, json, shutil, sys, os
WORK=Path('/kaggle/working')
COMFY=WORK/'ComfyUI'
INPUT=Path('/kaggle/input')
gpu=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,memory.free','--format=csv'],capture_output=True,text=True)
print(gpu.stdout or gpu.stderr)
if gpu.returncode: raise RuntimeError('No working GPU. Enable an accelerator before proceeding.')
print('Free working disk GiB:', round(shutil.disk_usage(WORK).free/2**30,1))
''')
code('''# Explicit opt-in: environment installation may use network and disk; no model downloads here.
INSTALL_ENVIRONMENT=False
if INSTALL_ENVIRONMENT:
    repos={str(COMFY):'https://github.com/comfyanonymous/ComfyUI.git',
       str(COMFY/'custom_nodes/ComfyUI-KJNodes'):'https://github.com/kijai/ComfyUI-KJNodes.git',
       str(COMFY/'custom_nodes/comfyui_controlnet_aux'):'https://github.com/Fannovel16/comfyui_controlnet_aux.git',
       str(COMFY/'custom_nodes/ComfyUI-segment-anything-2'):'https://github.com/kijai/ComfyUI-segment-anything-2.git'}
    revisions={}
    for dest,url in repos.items():
        p=Path(dest)
        if not p.exists(): subprocess.run(['git','clone','--depth','1',url,dest],check=True)
        revisions[url]=subprocess.check_output(['git','-C',dest,'rev-parse','HEAD'],text=True).strip()
        requirements=p/'requirements.txt'
        if requirements.exists(): subprocess.run([sys.executable,'-m','pip','install','-r',str(requirements)],check=True)
    (WORK/'installed-revisions.json').write_text(json.dumps(revisions,indent=2))
    print('Installed revisions saved. Keep this record with outputs.')
else: print('Skipped. Set INSTALL_ENVIRONMENT=True only when ready.')
''')
md('''## Models\nAttach model datasets and copy/symlink into the folders listed below. This package deliberately does not start tens of GB of downloads. FP8 Animate alone is large; 16GB GPU may require CPU offload and sufficient system RAM. No memory fit is guaranteed.\nOfficial guide: https://docs.comfy.org/tutorials/video/wan/wan2-2-animate\n- diffusion_models/Wan2_2-Animate-14B_fp8_e4m3fn_scaled_KJ.safetensors\n- text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors\n- vae/wan_2.1_vae.safetensors\n- clip_vision/clip_vision_h.safetensors\n- loras/lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors\nPose detector and SAM2 also need their own models; check node startup logs.\n''')
code('''REQUIRED={
'diffusion_models':'Wan2_2-Animate-14B_fp8_e4m3fn_scaled_KJ.safetensors',
'text_encoders':'umt5_xxl_fp8_e4m3fn_scaled.safetensors',
'vae':'wan_2.1_vae.safetensors',
'clip_vision':'clip_vision_h.safetensors',
'loras':'lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors'}
for folder,name in REQUIRED.items():
    path=COMFY/'models'/folder/name
    print('OK' if path.is_file() else 'MISSING',path)
''')
code('''def find_one(name):
    matches=list(INPUT.rglob(name))
    if len(matches)!=1: raise RuntimeError(f'Expected one {name}; found {len(matches)}. Attach the bundle/input dataset.')
    return matches[0]
SOURCE=find_one('source-zYt0aOGDwP0.mp4')
CHARACTER=find_one('tennis-woman-reference.png')
TEMPLATE=find_one('wan-animate-official-ui.json')
PREP=find_one('kaggle_recast_prepare.py')
subprocess.run([sys.executable,str(PREP),'--source',str(SOURCE),'--character',str(CHARACTER),'--workflow',str(TEMPLATE),'--comfy',str(COMFY),'--start','0'],check=True)
print((WORK/'recast-preflight.json').read_text())
''')
md('''## First-time mask and API export — required\nThe official template includes subgraphs and a Points Editor; `nodes/links` UI JSON is **not** `/prompt` API JSON. Open the prepared `tennis-recast-test-ui.json` in a separately accessible ComfyUI editor, select the central female performer in Points Editor, verify pose/face/mask, remove unnecessary Video Extend blocks for the short test, and export API JSON as `tennis-recast-api.json`.\nThis notebook supplies a headless local API server, **not** a public browser endpoint. Do not assume the localhost address is accessible from your home browser. If no ComfyUI editor is available, stop at preflight; a UI connection or an already prepared API graph is still needed.\nAttach the exported API JSON as an additional Kaggle input. Keep background_video and character_mask connected for Mix mode.\n''')
code('''# Start only after environment/models/input preparation and mask/API export are complete.
START_SERVER=False
if START_SERVER:
    log=open(WORK/'comfy-server.log','w')
    server=subprocess.Popen([sys.executable,str(COMFY/'main.py'),'--listen','127.0.0.1','--port','8188','--lowvram','--disable-auto-launch'],cwd=str(COMFY),stdout=log,stderr=subprocess.STDOUT)
    print('PID',server.pid,'Log:',WORK/'comfy-server.log')
''')
code('''# This is the only cell that submits a paid-in-GPU-time generation. No automatic retry.
RUN_GENERATION=False
if RUN_GENERATION:
    API=find_one('tennis-recast-api.json')
    RUNNER=find_one('comfy_api_run.py')
    subprocess.run([sys.executable,str(RUNNER),str(API),'--output-root',str(COMFY/'output'),'--exports',str(WORK/'exports')],check=True)
else: print('No generation submitted.')
''')
md('''## Review and save\nReview identity, skirt/shorts consistency, hands, ball, crowd occlusion and landing. Interpolation cannot repair wrong anatomy. Keep test outputs silent; original music is not automatically reused or published. Save a Kaggle version with outputs before ending the session.\nThe notebook has been syntax-checked locally, not executed on a Kaggle GPU.\n''')
j={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.10'}},'nbformat':4,'nbformat_minor':5}
(P/'kaggle-wan-animate-recast.ipynb').write_text(json.dumps(j,ensure_ascii=False,indent=2),encoding='utf8')
print('Created',len(cells),'cells')
