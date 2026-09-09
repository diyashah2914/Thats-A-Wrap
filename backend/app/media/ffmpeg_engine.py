import json, shutil, subprocess
from app.config import settings
from pathlib import Path
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
tracer=trace.get_tracer("thats-a-wrap-backend.media")
class FFmpegEngine:
    def __init__(self,root:str):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True); self.input=self.root/'input'; self.output=self.root/'output'; self.input.mkdir(exist_ok=True); self.output.mkdir(exist_ok=True)
    def available(self): return shutil.which('ffmpeg') is not None and shutil.which('ffprobe') is not None
    def probe(self,path): return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],text=True))
    def _run(self,cmd):
        with tracer.start_as_current_span("ffmpeg_command") as span:
            span.set_attribute("operation.type","ffmpeg_command"); span.set_attribute("media.engine","ffmpeg"); span.set_attribute("ffmpeg.command_length",len(cmd))
            result=subprocess.run(cmd,check=False,capture_output=True,text=True); span.set_attribute("ffmpeg.exit_code",int(result.returncode))
            if result.returncode:
                exc=RuntimeError(result.stderr[-2200:] or 'FFmpeg failed.'); span.record_exception(exc); span.set_status(Status(StatusCode.ERROR,str(exc))); span.set_attribute("operation.status","failed"); raise exc
            span.set_attribute("operation.status","success")
    def process(self,input_path,output_name,start=0,duration=None):
        return self.cinematic_process(input_path,output_name,{"color_grade":"cinematic","vfx":["subtle vignette","clarity"],"cinematography":["stable framing"],"audio":["dialogue normalization"],"transition":"fade in/out"},start=start,duration=duration)
    def cinematic_process(self,input_path,output_name,plan,start=0,duration=None):
        out=self.output/output_name; info=self.probe(input_path); streams=info.get('streams',[]); has_audio=any(s.get('codec_type')=='audio' for s in streams)
        source_duration=float(info.get('format',{}).get('duration',0) or 0)
        if duration is not None: source_duration=min(source_duration,float(duration)) if source_duration else float(duration)
        filters=['scale=1280:720:force_original_aspect_ratio=decrease','pad=1280:720:(ow-iw)/2:(oh-ih)/2']
        grade=str(plan.get('color_grade','cinematic')).lower()
        if 'warm' in grade: filters.append('eq=contrast=1.08:brightness=0.02:saturation=1.08')
        elif 'cool' in grade: filters.append('eq=contrast=1.10:brightness=0.00:saturation=0.94')
        elif 'dramatic' in grade: filters.append('eq=contrast=1.16:brightness=-0.02:saturation=0.96')
        else: filters.append('eq=contrast=1.08:brightness=0.01:saturation=1.04')
        vfx=[str(x).lower() for x in plan.get('vfx',[])]
        if any('sharp' in x or 'clarity' in x for x in vfx): filters.append('unsharp=5:5:0.55:5:5:0.0')
        if any('vignette' in x for x in vfx): filters.append('vignette=PI/5')
        if any('glow' in x for x in vfx): filters.append('gblur=sigma=0.7')
        if any('motion' in x for x in vfx): filters.append('eq=saturation=1.03:contrast=1.03')
        if str(plan.get('transition','cut')) in ('fade in/out','fade'):
            filters.append('fade=t=in:st=0:d=0.35')
            if source_duration>0.8: filters.append(f'fade=t=out:st={max(0.1,source_duration-0.35):.3f}:d=0.35')
        music=plan.get('music') or {}; music_enabled=bool(music.get('enabled',True)); music_name=str(music.get('track','minimal_ambient')); music_path=self.root/'music'/f'{music_name}.mp3'; use_music=music_enabled and music_path.exists()
        cmd=['ffmpeg','-y'];
        if start>0: cmd += ['-ss',str(start)]
        cmd += ['-i',str(input_path)]
        if use_music: cmd += ['-stream_loop','-1','-i',str(music_path)]
        if duration is not None: cmd += ['-t',str(duration)]
        if use_music:
            vol=max(0.0,min(0.6,float(music.get('volume',0.18)))); fade_in=max(0.0,min(10.0,float(music.get('fade_in_seconds',1.2)))); fade_out=max(0.0,min(10.0,float(music.get('fade_out_seconds',1.5)))); trim_end=max(0.1,source_duration)
            mf=f'[1:a]atrim=0:{trim_end:.3f},asetpts=N/SR/TB,volume={vol:.3f}'
            if fade_in>0: mf+=f',afade=t=in:st=0:d={min(fade_in,trim_end):.3f}'
            if fade_out>0 and trim_end>fade_out: mf+=f',afade=t=out:st={max(0,trim_end-fade_out):.3f}:d={fade_out:.3f}'
            mf+='[music]'
            if has_audio:
                af=(f'[0:a]aresample=48000,loudnorm=I=-16:LRA=11:TP=-1.5,apad=pad_dur={trim_end:.3f}[dialogue];'+mf+f';[music]apad=pad_dur={trim_end:.3f}[music_full];[music_full][dialogue]sidechaincompress=threshold=0.02:ratio=5:attack=20:release=300[ducked];[dialogue][ducked]amix=inputs=2:duration=longest:dropout_transition=2:weights=1 1[mix];[mix]loudnorm=I=-16:LRA=11:TP=-1.5,apad,atrim=0:{trim_end:.3f},asetpts=N/SR/TB[aout]')
            else: af=mf+';[music]apad=pad_dur=1[aout]'
            cmd += ['-filter_complex','[0:v]'+','.join(filters)+'[vout];'+af,'-map','[vout]','-map','[aout]','-c:v','libx264','-preset',settings.ffmpeg_preset,'-crf',str(settings.ffmpeg_crf),'-c:a','aac','-b:a','192k','-t',f'{trim_end:.3f}']
        else:
            cmd += ['-vf',','.join(filters),'-an'] if not has_audio else ['-vf',','.join(filters),'-map','0:v:0','-map','0:a:0?','-c:a','aac','-b:a','192k','-af',f'loudnorm=I=-16:LRA=11:TP=-1.5,apad,atrim=0:{source_duration:.3f},asetpts=N/SR/TB','-t',f'{source_duration:.3f}']
            if not has_audio: cmd += ['-map','0:v:0']
            cmd += ['-c:v','libx264','-preset',settings.ffmpeg_preset,'-crf',str(settings.ffmpeg_crf)]
        cmd += ['-threads','0','-movflags','+faststart',str(out)]; self._run(cmd); return str(out)
    def trim(self,input_path,output_name,start,duration): return self.process(input_path,output_name,start,duration)
    def extract_audio(self,input_path,output_name): out=self.output/output_name; self._run(['ffmpeg','-y','-i',str(input_path),'-vn','-c:a','aac','-b:a','192k',str(out)]); return str(out)
    def normalize_audio(self,input_path,output_name): out=self.output/output_name; self._run(['ffmpeg','-y','-i',str(input_path),'-af','loudnorm=I=-16:LRA=11:TP=-1.5','-c:v','copy','-c:a','aac',str(out)]); return str(out)
    def replace_audio(self,video_path,audio_path,output_name): out=self.output/output_name; self._run(['ffmpeg','-y','-i',str(video_path),'-i',str(audio_path),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-shortest',str(out)]); return str(out)
    def mix_audio(self,video_path,audio_path,output_name,music_volume=.20): out=self.output/output_name; filt=f'[1:a]volume={music_volume}[music];[0:a][music]amix=inputs=2:duration=longest:dropout_transition=2[a]'; self._run(['ffmpeg','-y','-i',str(video_path),'-i',str(audio_path),'-filter_complex',filt,'-map','0:v:0','-map','[a]','-c:v','copy','-c:a','aac',str(out)]); return str(out)
    def concat(self,inputs,output_name='final_film.mp4',plan=None):
        if not inputs: raise ValueError('No inputs supplied for concatenation.')
        out=self.output/output_name; plan=plan or {}; transition=str(plan.get('transition','crossfade')); trans=max(0.0,min(1.2,float(plan.get('transition_duration',0.65))))
        if len(inputs)==1:
            self._run(['ffmpeg','-y','-i',str(inputs[0]),'-c:v','libx264','-preset',settings.ffmpeg_preset,'-crf',str(settings.ffmpeg_crf),'-c:a','aac','-b:a','192k','-threads','0','-movflags','+faststart',str(out)]); return str(out)
        durations=[float(self.probe(p).get('format',{}).get('duration',0) or 0) for p in inputs]
        if transition=='crossfade' and all(d>trans+0.1 for d in durations):
            cmd=['ffmpeg','-y']; [cmd.extend(['-i',str(p)]) for p in inputs]; parts=[]
            for i in range(len(inputs)):
                parts += [f'[{i}:v]settb=AVTB,format=yuv420p[v{i}]',f'[{i}:a]aresample=48000,asetpts=N/SR/TB[a{i}]']
            cur_v='[v0]'; cur_a='[a0]'; cumulative=durations[0]
            for i in range(1,len(inputs)):
                off=max(0.0,cumulative-trans); nv=f'[vx{i}]'; na=f'[ax{i}]'
                parts.append(f'{cur_v}[v{i}]xfade=transition=fade:duration={trans:.3f}:offset={off:.3f}{nv}')
                parts.append(f'{cur_a}[a{i}]acrossfade=d={trans:.3f}:c1=tri:c2=tri{na}')
                cur_v,cur_a=nv,na; cumulative += durations[i]-trans
            try:
                self._run(cmd+['-filter_complex',';'.join(parts),'-map',cur_v,'-map',cur_a,'-c:v','libx264','-preset',settings.ffmpeg_preset,'-crf',str(settings.ffmpeg_crf),'-c:a','aac','-b:a','192k','-threads','0','-movflags','+faststart',str(out)]); return str(out)
            except RuntimeError: pass
        list_file=self.output/'concat.txt'; list_file.write_text('\n'.join(f"file '{Path(p).resolve()}'" for p in inputs),encoding='utf8')
        self._run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(list_file),'-c:v','libx264','-preset',settings.ffmpeg_preset,'-crf',str(settings.ffmpeg_crf),'-c:a','aac','-b:a','192k','-threads','0','-movflags','+faststart',str(out)]); return str(out)
