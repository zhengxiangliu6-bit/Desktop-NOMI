import { useEffect, useRef, useState } from 'react';
import { hardwareExpressions } from './expressions.generated';
import { HardwareFace } from './HardwareFace';
import './hardware.css';

export function HardwareGallery() {
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [replay, setReplay] = useState(0);
  const section = useRef<HTMLElement>(null);
  const current = hardwareExpressions[index] ?? hardwareExpressions[0];
  useEffect(() => {
    if (window.location.hash === '#hardware-expressions') section.current?.scrollIntoView();
  }, []);
  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => { setIndex(i => (i+1)%hardwareExpressions.length); setReplay(n=>n+1); }, 3000);
    return () => window.clearInterval(timer);
  }, [playing]);
  return <section id="hardware-expressions" ref={section} className="hw-gallery" aria-label="圆屏表情实验室">
    <div className="hw-heading"><div><p className="eyebrow">ROUND SCREEN · EXPRESSION LAB</p><h2>14种圆屏表情</h2>
      <p>看清每一种小情绪，再到设备上试一试。</p></div>
      <button type="button" className="hw-play" aria-pressed={playing} onClick={()=>setPlaying(v=>!v)}>{playing?'暂停轮播':'循环演示14种'}</button>
    </div>
    <div className="hw-preview">
      <div className="hw-live" role="group" aria-label="当前圆屏预览"><HardwareFace key={`${index}-${replay}`} expression={current} animated /></div>
      <div className="hw-description" aria-live="polite">
        <p className="hw-number">{String(index+1).padStart(2,'0')} / 14</p>
        <h3>{current.label}<code>{current.command}</code></h3><p>{current.description}</p>
        <p className="hw-say">设备上说：<strong>“{current.voices[0]}”</strong></p>
        <button type="button" onClick={()=>setReplay(n=>n+1)}>重播当前表情</button>
        <p className="hw-note">先说“小米同学”，再说指令。这里仅预览表情，不连接麦克风或控制硬件。</p>
      </div>
    </div>
    <div className="hw-grid" aria-label="选择圆屏表情">
      {hardwareExpressions.map((e,i)=><button type="button" key={e.command} aria-label={`圆屏${e.label}`} aria-pressed={index===i}
        className={`hw-card ${index===i?'is-selected':''}`} onClick={()=>{setPlaying(false);setIndex(i);setReplay(n=>n+1);}}>
        <HardwareFace expression={e}/><span>{e.label}</span><code>{e.command}</code>
      </button>)}
    </div>
    <p className="hw-footnote">360×360 圆屏设计 · 眉眼与嘴形各有区别 · 页面的聊天 Mock 演示独立保留</p>
  </section>;
}
