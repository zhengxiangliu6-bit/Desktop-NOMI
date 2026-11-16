import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { HardwareGallery } from './HardwareGallery';
import { hardwareExpressions } from './expressions.generated';

afterEach(()=>vi.useRealTimers());
describe('round screen expression gallery',()=>{
  it('has fourteen distinct controls and matching voice instructions without changing chat APIs',()=>{
    render(<HardwareGallery/>);
    expect(hardwareExpressions).toHaveLength(14);
    expect(new Set(hardwareExpressions.map(e=>e.command)).size).toBe(14);
    for(const e of hardwareExpressions) expect(screen.getByRole('button',{name:`圆屏${e.label}`})).toBeEnabled();
    fireEvent.click(screen.getByRole('button',{name:'圆屏生气'}));
    const preview=within(screen.getByRole('group',{name:'当前圆屏预览'}));
    expect(preview.getByRole('img',{name:'圆屏：生气（angry）'})).toBeVisible();
    expect(screen.getByText('“生气一点”')).toBeVisible();
    expect(screen.getByRole('button',{name:'圆屏生气'})).toHaveAttribute('aria-pressed','true');
  });
  it('cycles through expressions and manual selection stops playback',()=>{
    vi.useFakeTimers();render(<HardwareGallery/>);
    fireEvent.click(screen.getByRole('button',{name:'循环演示14种'}));
    act(()=>vi.advanceTimersByTime(3000));
    expect(screen.getByRole('button',{name:'圆屏眨眼'})).toHaveAttribute('aria-pressed','true');
    fireEvent.click(screen.getByRole('button',{name:'圆屏喜欢'}));
    act(()=>vi.advanceTimersByTime(6000));
    expect(screen.getByRole('button',{name:'圆屏喜欢'})).toHaveAttribute('aria-pressed','true');
    expect(screen.getByRole('button',{name:'循环演示14种'})).toHaveAttribute('aria-pressed','false');
  });
});
