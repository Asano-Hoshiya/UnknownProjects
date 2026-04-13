# Transyes Image Folder Plan

## Recommendation

Yes, the code will eventually need image paths, but the safest approach is:

1. Store all generated images under `transyes/assets/images/`
2. Keep image URLs relative to `assets/css/site.css`, not absolute like `/transyes/...`
3. Prefer CSS `background-image: url("../images/...")` for hero panels, banners, cards, and QR placeholders
4. Avoid root-absolute image paths so the site still works if the deployment folder changes again

## Suggested Structure

```text
assets/images/
  shared/
  icons/
  logos/
  qr/
  zh/
    home/
    about/
    quote/
    industries/
    cases/
    resources/
    services/
  en/
    home/
    about/
    quote/
    industries/
    insights/
    services/
  light/
    fr/
    es/
    de/
    ar/
```

## Important Notes

- `中国人民银行 / 故宫博物院 / 中国日报 / UNDP / CCTV / 微软中国` 这些不能用 AI 生成 logo，应该使用真实授权 logo，或继续保留文字版。
- `微信 QR` 也不该用 AI 生成，应该替换成真实二维码图片。
- 当前代码里大多数位置还是占位 `div.panel / div.wide / div.icon / div.qr`，还没有真正的图片路径。
- 所以现在最适合的顺序是：
  1. 先按 `IMAGE_PROMPTS.md` 生成图片
  2. 把图片放进这个目录
  3. 再统一把占位块替换成图片类名或背景图路径

## Why Not Use `/transyes/...`

站点之前已经从 `transyes-site-v3_5` 改成 `transyes` 一次了。  
如果图片路径也写死成 `/transyes/...`，以后目录再变时还要整站重改。  
把路径放在 CSS 里并使用 `../images/...`，后续维护会稳很多。
