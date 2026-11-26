import { useEffect, useRef } from 'react';

// Original synthesized audio: no downloaded tracks, subscriptions or asset files.
export function useRoyaleAudio(enabled: boolean, atTable: boolean, pileSize: number) {
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
      tone(ctx,notes[beat++%notes.length],atTable?.025:.019,atTable?.48:.73,atTable?'sine':'triangle');
    },atTable?415:570);
    return ()=>{window.clearInterval(interval);window.removeEventListener('pointerdown',mine);window.removeEventListener('keydown',mine);};
  },[enabled,atTable]);
  useEffect(()=>{
    const ctx=context.current;
    if(enabled&&atTable&&previous.current>=0&&pileSize>previous.current&&ctx?.state==='running')tone(ctx,310,.075,.09,'triangle');
    previous.current=atTable?pileSize:-1;
  },[enabled,atTable,pileSize]);
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
