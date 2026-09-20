#!/usr/bin/env python3
"""Add Chinese per-assignment documentation without exporting or displaying values."""
import argparse
import json
import os
import re
import tempfile
from pathlib import Path


def model_keys():
 data=json.loads((Path(__file__).resolve().parents[1]/'plugin/src/drama_plugin/providers/video/registry.json').read_text())
 return set(data['models']) | set(data['legacy_model_keys'])


def model_enabled_env(model):
 return 'DRAMA_VIDEO_MODEL_'+re.sub(r'[^A-Z0-9]','_',model.upper())+'_ENABLED'

ASSIGN = re.compile(r'^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=')
PROVIDERS = {'SEEDANCE':('Seedance','https://ark.cn-beijing.volces.com/api/v3'),
 'MINIMAX':('MiniMax','https://api.minimaxi.com'),'VIDU':('Vidu','https://api.vidu.com'),
 'WAN':('Wan',''),'KLING':('Kling','')}
COMMENTS = {
 'rhythm_speed':'剧情节奏倍率，由 Plugin 上下文层在创作时读取；可选，省略使用默认节奏，不建议留空。',
 'DRAMA_PLUGIN_PROVIDER_AUDIO_SEMANTIC_MODE':'音视频语义观察 Provider 开关，由 Plugin 初始化时读取；可选，off 禁用，留空不启用远程观察。',
 'DRAMA_PLUGIN_PROVIDER_QWEN_OMNI_API_KEY':'通义音视频观察 API 密钥，由观察适配器鉴权时使用；启用观察时必填，留空表示未配置。',
 'DRAMA_PLUGIN_PROVIDER_QWEN_OMNI_BASE_URL':'通义音视频观察官方服务地址，由观察适配器发送请求时使用；启用观察时必填，留空不能调用。',
 'DRAMA_PLUGIN_PROVIDER_QWEN_OMNI_MODEL':'通义观察模型名称，由已有音视频观察适配器使用；可选，省略使用内置默认值，非本轮视频生成模型。',
 'DRAMA_PLUGIN_PROVIDER_QWEN_OMNI_REASONING_EFFORT':'通义观察推理强度，由音视频观察请求使用；可选，none 表示不开启额外推理，省略使用默认值。',
 'DRAMA_PLUGIN_PROVIDER_QWEN_OMNI_USE_MULTICHANNEL':'多声道观察开关，由音视频语义观察使用；可选，false 关闭，省略使用默认值。',
 'DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS':'媒体本地导入允许目录，由 Plugin 导入文件时检查；可选，留空使用服务默认限制，不代表任意目录放行。',
 'DRAMA_PLUGIN_ROLE_DUBBING_OUTPUT_DIRECTORY':'角色配音临时输出目录，由配音适配器保存合成音频时使用；启用配音时必填，留空无法落盘。',
 'DRAMA_PLUGIN_ROLE_DUBBING_TIMEOUT_SECONDS':'配音请求超时秒数，由配音适配器调用时使用；可选，省略使用内置默认值，留空不是零秒。',
 'FISH_AUDIO_API_KEY':'Fish Audio 配音密钥，由角色配音 Provider 鉴权使用；可选，留空禁用真实配音调用。',
 'FISH_AUDIO_BASE_URL':'Fish Audio 官方服务地址，由配音 Provider 发起请求时使用；可选，省略使用内置地址，留空不提供可用地址。',
 'FISH_TTS_MODEL':'现有 Fish 配音模型名称，由语音合成适配器使用；可选，省略使用默认模型，非视频生成模型配置。',
 'DRAMA_PLUGIN_VIDEO_ROUTE_MODE':'已有视频路线偏好模式，由路线选择器读取；可选，auto 自动比较，prefer 按偏好尝试，pin 锁定；留空等同 auto。',
 'DRAMA_PLUGIN_VIDEO_MODEL_PREFERRED':'已有路线兼容偏好键，由选择器在 prefer 或 pin 时使用；auto 可留空，能力与正式模型 ID 仍由 Registry 管理。',
 'DRAMA_PLUGIN_VIDEO_MODEL_FALLBACKS':'已有路线兼容回退键列表，由 prefer 模式按逗号顺序读取；可选，留空无指定回退，pin 时不生效。',
}
for part, label in {'MEMORY':'剧情存储','ASSET':'资产','RESEARCH':'研究','PRODUCTION':'旧生产转发','MEDIA':'媒体','CONTEXT':'上下文','VOICE':'声音身份'}.items():
 COMMENTS[f'DRAMA_PLUGIN_PROVIDER_{part}_MODE']=f'{label} Provider 模式，由 Plugin 初始化时选择本地模拟或远程服务；可选，省略使用默认值，http 需配置对应地址和令牌。'
 COMMENTS[f'DRAMA_PLUGIN_SERVICE_{part}_BASE_URL']=f'{label}服务地址，由对应 HTTP Provider 调用现有 Drama Service；http 模式必填，留空表示未配置远程地址。'
 COMMENTS[f'DRAMA_PLUGIN_SERVICE_{part}_API_TOKEN']=f'{label}服务访问令牌，由对应 HTTP Provider 鉴权使用；http 模式必填，留空不能调用，禁止提交到 Git。'
 COMMENTS[f'DRAMA_PLUGIN_SERVICE_{part}_TIMEOUT_SECONDS']=f'{label}服务请求超时秒数，由对应 HTTP Provider 使用；可选，省略使用内置默认值，填写正数，勿留空。'
for p,(label,base) in PROVIDERS.items():
 COMMENTS[f'DRAMA_VIDEO_{p}_API_KEY']=f'{label} 官方视频 API 密钥，由视频 HTTP Provider 鉴权时使用；可选，留空仅禁用该 Provider，不影响 Plugin 启动。'
 COMMENTS[f'DRAMA_VIDEO_{p}_BASE_URL']=f'{label} 官方视频 API 基础地址，由视频 HTTP Provider 按账号区域调用；启用时必填，留空仅禁用该 Provider。'+('Wan 需包含正确 Workspace、Region 和 /api/v1。' if p=='WAN' else 'Kling 必须使用当前官方文档的服务地址。' if p=='KLING' else '省略变量时可使用内置默认地址。')
for model in sorted(model_keys()):
 COMMENTS[model_enabled_env(model)]=f'{model} 视频模型启用开关，由路线选择与新任务提交门禁读取；true 才允许候选，false、空值或非法值禁用；可选，省略沿用 true；不影响已提交任务的查询回收。'


def assignments(text):
 return {m.group(1):line for line in text.splitlines() if (m:=ASSIGN.match(line.strip()))}


def annotate(text):
 out=[]
 for line in text.splitlines():
  m=ASSIGN.match(line.strip())
  if m:
   key=m.group(1)
   if key not in COMMENTS: raise ValueError('UNDOCUMENTED_KEY:'+key)
   comment='# '+COMMENTS[key]
   if not out or out[-1]!=comment: out.append(comment)
  out.append(line)
 return '\n'.join(out)+'\n'


def validate_comments(text):
 lines=text.splitlines()
 missing=[m.group(1) for i,line in enumerate(lines) if (m:=ASSIGN.match(line.strip())) and
          (i==0 or not lines[i-1].startswith('# ') or not re.search('[\u4e00-\u9fff]',lines[i-1]))]
 if missing: raise ValueError('CHINESE_COMMENT_MISSING:'+','.join(missing))
 return len(assignments(text))


def update(path,add_video=False,add_model_flags=False):
 old=path.read_text(); prior=assignments(old)
 if add_video:
  for p,(_,base) in PROVIDERS.items():
   for suffix,value in [('API_KEY',''),('BASE_URL',base)]:
    key=f'DRAMA_VIDEO_{p}_{suffix}'
    if key not in prior: old+='\n'+key+'='+value+'\n'
 if add_model_flags:
  for model in sorted(model_keys()):
   key=model_enabled_env(model)
   if key not in prior: old+='\n'+key+'=true\n'
 new=annotate(old)
 if any(assignments(new).get(k)!=line for k,line in prior.items()): raise ValueError('VALUE_PRESERVATION_FAILED')
 count=validate_comments(new)
 fd,tmp=tempfile.mkstemp(prefix='.env-comments-',dir=path.parent)
 try:
  with os.fdopen(fd,'w') as f: f.write(new)
  os.chmod(tmp,path.stat().st_mode & 0o777)
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp): os.unlink(tmp)
 return {'assignments':count,'existingValuesPreserved':True,'chineseComments':'PASS'}


def main():
 p=argparse.ArgumentParser();p.add_argument('path',type=Path);p.add_argument('--add-video',action='store_true');p.add_argument('--add-model-flags',action='store_true');p.add_argument('--check',action='store_true');a=p.parse_args()
 result={'assignments':validate_comments(a.path.read_text()),'chineseComments':'PASS'} if a.check else update(a.path,a.add_video,a.add_model_flags)
 print(json.dumps(result))
if __name__=='__main__':main()
