import { test, expect } from '@playwright/test';
test('static round screen gallery includes every hardware expression and works on mobile',async({page})=>{
  const requests:string[]=[];
  page.on('request',r=>{if(r.url().includes('/api/'))requests.push(r.url());});
  await page.goto('./#hardware-expressions');
  const gallery=page.getByRole('region',{name:'圆屏表情实验室'});
  await expect(gallery.getByRole('button',{name:/^圆屏/})).toHaveCount(14);
  for(const label of ['生气','惊讶','困倦','单眼眨眼','喜欢','疑惑']){
    await gallery.getByRole('button',{name:`圆屏${label}`,exact:true}).click();
    await expect(gallery.getByRole('group',{name:'当前圆屏预览'}).getByRole('img')).toHaveAccessibleName(new RegExp(label));
  }
  await gallery.getByRole('button',{name:'循环演示14种'}).click();
  await expect(gallery.getByRole('button',{name:'暂停轮播'})).toHaveAttribute('aria-pressed','true');
  await gallery.getByRole('button',{name:'圆屏开心',exact:true}).click();
  await expect(gallery.getByRole('button',{name:'循环演示14种'})).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  await gallery.scrollIntoViewIfNeeded();
  await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
  await page.reload();await expect(gallery).toBeVisible();
  expect(requests).toEqual([]);
});
