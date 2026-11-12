import os,pathlib,sys
ROOT=pathlib.Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else pathlib.Path(__file__).resolve().parents[1]
if getattr(sys,'frozen',False) and ROOT.parent.name=='.programs':ROOT=ROOT.parent.parent
CODEX_HOME=pathlib.Path(os.environ.get('CODEX_HOME',pathlib.Path.home()/'.codex'))
VERSION='1.0.1'
APP_NAME='赛琳娜Codex桌宠启动'
EXECUTABLE_NAME=APP_NAME+'.exe'
PORTABLE_DIRNAME='赛琳娜Codex桌宠'
AUDIO_SESSION_NAME='赛琳娜 · Codex'
APPLICATION_ID='Doya16.Selena.Codex'

UPDATE_REPOSITORY='Doya16/selena-codex-pet'
