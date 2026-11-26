import { useEffect, useRef } from 'react';

// Original synthesized audio: no downloaded tracks, subscriptions or asset files.
export function useRoyaleAudio(enabled: boolean, atTable: boolean, pileSize: number, eventSignature = '') {
  const context = useRef<AudioContext|null>(null);
  const previous = useRef(-1);
  useEffect(()=>{
    if(!enabled)return;
    let beat=0;
    const mine=()=>{
      if(!context.current || context.current.state==='closed') context.current=new AudioContext();
      void context.current.resume().catch(()=>{});
    };
    window.addEventListener('pointerdown',mine);
    window.addEventListener('keydown',mine);
    const interval=window.setInterval(()=>{
      const ctx=context.current;
      if(!ctx||ctx.state!=='running'||document.hidden)return;
      const notes=atTable?[110,165,130.81,164.81,110,146.83,123.47,164.81]:[130.81,196,246.94,293.66,110,164.81,220,261.63];
      const note=notes[beat++%notes.length];
      tone(ctx,note,atTable?.022:.018,atTable?.58:.76,atTable?'sine':'triangle');
      if(atTable&&beat%4===0)tone(ctx,note/2,.008,.9,'sine');
    },atTable?480:590);
    return ()=>{window.clearInterval(interval);window.removeEventListener('pointerdown',mine);window.removeEventListener('keydown',mine);};
  },[enabled,atTable]);
  useEffect(()=>{
    const ctx=context.current;
    if(enabled&&atTable&&previous.current>=0&&pileSize>previous.current&&ctx?.state==='running')tone(ctx,310,.075,.09,'triangle');
    previous.current=atTable?pileSize:-1;
  },[enabled,atTable,pileSize]);
  useEffect(()=>{
    if(!enabled||!atTable||!eventSignature)return;
    const ctx=context.current;
    if(!ctx||ctx.state!=='running')return;
    const [type,variant]=eventSignature.split(':');
    const sounds:Record<string,number[]>={play:[392],skip:[294],challenge_bluff:[523,392,262],challenge_truth:[392,523,659],pause:[330,247],timeout_pause:[330,247],resume:[392,523],leave:[262,220],finished:[523,659,784],close_round:[440,554]};
    const notes=sounds[type==='challenge'?`challenge_${variant}`:type];
    if(!notes)return;
    notes.forEach((note,index)=>window.setTimeout(()=>{
      if(context.current?.state==='running')tone(context.current,note,.055,.16,'triangle');
    },index*105));
  },[enabled,atTable,eventSignature]);
  useEffect(()=>()=>{const ctx=context.current;context.current=null;if(ctx&&ctx.state!=='closed')void ctx.close().catch(()=>{});},[]);
}
function tone(ctx:AudioContext,hz:number,volume:number,duration:number,type:OscillatorType){
  const osc=ctx.createOscillator(), gain=ctx.createGain(), now=ctx.currentTime;
  osc.type=type;osc.frequency.value=hz;
  gain.gain.setValueAtTime(.0001,now);
  gain.gain.exponentialRampToValueAtTime(volume,now+.03);
  gain.gain.exponentialRampToValueAtTime(.0001,now+duration);
  osc.connect(gain);gain.connect(ctx.destination);osc.start(now);osc.stop(now+duration+.01);
  osc.onended=()=>{osc.disconnect();gain.disconnect();};
}
