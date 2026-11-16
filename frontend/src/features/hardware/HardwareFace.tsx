import type { HardwareExpression } from './expressions.generated';

export function HardwareFace({ expression: e, animated = false }: { expression: HardwareExpression; animated?: boolean }) {
  const p = e.pose;
  const mouth = Array.from({ length: 9 }, (_, i) => {
    const x = i / 8;
    return `${151 + x * 58},${229 + (e.mouth === 'zigzag' ? 14 + (i % 2 ? 5 : -5) : 14 + p.mouth_curve * (1 - (2*x-1)**2))}`;
  }).join(' ');
  const heart = '24,43 2,21 2,9 10,2 19,2 24,10 29,2 38,2 46,9 46,21 24,43';
  return <svg viewBox="0 0 360 360" role="img" aria-label={`圆屏：${e.label}（${e.command}）`}
    className={`hw-face hw-${e.command} ${animated ? 'is-animated' : ''}`}>
    <circle cx="180" cy="180" r="179" fill="#fff0d4" />
    {e.decor === 'ring' && <circle className="hw-listen-ring" cx="180" cy="180" r="142" fill="none" stroke="#e8a26e" strokeWidth="4" />}
    <g fill="#e8a26e" opacity=".5"><rect x="74" y="205" width="28" height="12" rx="6"/><rect x="258" y="205" width="28" height="12" rx="6"/></g>
    <g className="hw-eyes">
      {[0,1].map(i => {
        const cx = (i ? 240 : 120) + p.gaze_x, cy = 160+p.gaze_y;
        const width = i ? p.right_width : p.left_width;
        const height = e.command === 'blink' && !animated ? 4 : i ? p.right_height : p.left_height;
        return <g key={i}>
          {e.eyes === 'normal' && <rect x={cx-width/2} y={cy-height/2} width={width} height={height} rx={Math.min(width,height)/2} fill="#283445"/>}
          {e.eyes === 'smile' && <polyline points={Array.from({length:9},(_,j)=>`${cx-width/2+j/8*width},${cy-7+14*(2*j/8-1)**2}`).join(' ')} fill="none" stroke="#283445" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round"/>}
          {e.eyes === 'heart' && <polyline points={heart} transform={`translate(${cx-24} ${cy-23})`} fill="none" stroke="#d76888" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round"/>}
        </g>;
      })}
    </g>
    {[0,1].map(i => {
      const cx = (i ? 240 : 120)+p.gaze_x, angle = i ? p.brow_right : p.brow_left;
      return <line key={i} x1={cx-24} y1={106+p.gaze_y+p.brow_raise-angle/2} x2={cx+24} y2={106+p.gaze_y+p.brow_raise+angle/2}
        stroke="#283445" strokeWidth="5" strokeLinecap="round" opacity={p.brow_opa}/>;
    })}
    {p.mouth_open > 1 ? <rect className="hw-open-mouth" x={180-(e.command==='surprised'?42:26)/2} y={245-p.mouth_open/2}
      width={e.command==='surprised'?42:26} height={p.mouth_open} rx={Math.min(p.mouth_open,e.command==='surprised'?42:26)/2} fill="#283445"/> :
      <polyline points={mouth} fill="none" stroke="#283445" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"/>}
    {e.decor === 'tears' && <g className="hw-tears" fill="#72b7d2"><rect x="93" y="187" width="10" height="28" rx="5"/><rect x="257" y="187" width="10" height="28" rx="5"/></g>}
    {e.decor === 'dots' && [0,1,2].map(i=><circle key={i} className={`hw-dot hw-dot-${i}`} cx={160+i*20} cy="284" r="4" fill="#283445"/>)}
    {e.decor === 'anger' && <g stroke="#d86052" strokeWidth="4" fill="none" strokeLinejoin="round">
      {[0,1,2,3].map(i=><polyline key={i} points={`${266+(i%2?12:0)},${107+(i>1?12:0)} ${266+(i%2?12:0)},${99+(i>1?12:0)} ${274+(i%2?12:0)},${99+(i>1?12:0)}`}/>)}</g>}
    {['sleep','question','exclaim'].includes(e.decor) && <g fill="#283445" fontFamily="Arial, sans-serif" fontSize="14" fontWeight="700">
      {(e.decor==='sleep'?[0,1,2]:[0]).map(i=><text key={i} x={250+i*12} y={106-i*14}>{e.decor==='sleep'?'Z':e.decor==='question'?'?':'!'}</text>)}</g>}
  </svg>;
}
