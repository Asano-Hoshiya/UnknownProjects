function bindNavToggles() {
  document.querySelectorAll("[data-nav]").forEach((button) => {
    if (button.dataset.boundNav === "1") return;
    button.dataset.boundNav = "1";
    button.addEventListener("click", () => {
      const target = document.querySelector(button.dataset.nav);
      if (target) target.classList.toggle("open");
    });
  });
}

function bindFaqs() {
  document.querySelectorAll(".faq").forEach((item) => {
    const button = item.querySelector(".faqbtn");
    if (button && button.dataset.boundFaq !== "1") {
      button.dataset.boundFaq = "1";
      button.addEventListener("click", () => item.classList.toggle("open"));
    }
  });
}

function initTypedText() {
  const el = document.querySelector("[data-typed]");
  if (!el || el.dataset.typedInit === "1") return;
  el.dataset.typedInit = "1";

  const phrases = (el.dataset.typed || "")
    .split("|")
    .map((value) => value.trim())
    .filter(Boolean);

  if (!phrases.length) return;

  if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
    el.textContent = phrases[0];
    return;
  }

  let phraseIndex = 0;
  let charIndex = 0;
  let deleting = false;

  const tick = () => {
    const phrase = phrases[phraseIndex];

    if (!deleting) {
      el.textContent = phrase.slice(0, charIndex + 1);
      charIndex += 1;

      if (charIndex === phrase.length) {
        deleting = true;
        setTimeout(tick, 1500);
        return;
      }

      setTimeout(tick, 68);
      return;
    }

    el.textContent = phrase.slice(0, charIndex - 1);
    charIndex -= 1;

    if (charIndex <= 0) {
      deleting = false;
      phraseIndex = (phraseIndex + 1) % phrases.length;
      setTimeout(tick, 340);
      return;
    }

    setTimeout(tick, 34);
  };

  tick();
}

function initMediaBlocks() {
  const buildFallbackLabel = (node) => {
    if (node.querySelector(".media-label")) return;

    const lang = (document.documentElement.lang || "").toLowerCase();
    const isZh = lang.startsWith("zh");
    const isEn = lang.startsWith("en");
    const isFr = lang.startsWith("fr");
    const isEs = lang.startsWith("es");
    const isDe = lang.startsWith("de");
    const isAr = lang.startsWith("ar");
    const isQr = node.classList.contains("media-qr-wechat");
    const isIcon = node.classList.contains("icon");

    let labelHtml = "<strong>Image placeholder</strong>";

    if (isQr) {
      if (isZh) labelHtml = "微信 QR";
      else if (isFr) labelHtml = "QR WeChat";
      else if (isEs) labelHtml = "QR de WeChat";
      else if (isDe) labelHtml = "WeChat QR";
      else if (isAr) labelHtml = "رمز QR لـ WeChat";
      else labelHtml = "WeChat QR";
    } else if (isIcon) {
      if (isZh) labelHtml = "<strong>图标占位</strong>";
      else if (isFr) labelHtml = "<strong>Icône de remplacement</strong>";
      else if (isEs) labelHtml = "<strong>Icono de marcador</strong>";
      else if (isDe) labelHtml = "<strong>Icon-Platzhalter</strong>";
      else if (isAr) labelHtml = "<strong>عنصر أيقونة بديل</strong>";
      else labelHtml = "<strong>Icon placeholder</strong>";
    } else {
      if (isZh) labelHtml = "<strong>图片占位</strong>";
      else if (isFr) labelHtml = "<strong>Visuel de remplacement</strong>";
      else if (isEs) labelHtml = "<strong>Imagen de marcador</strong>";
      else if (isDe) labelHtml = "<strong>Bild-Platzhalter</strong>";
      else if (isAr) labelHtml = "<strong>عنصر بصري بديل</strong>";
    }

    const label = document.createElement("div");
    label.className = "media-label";
    label.innerHTML = labelHtml;
    node.appendChild(label);
  };

  const stylesheetNode = document.querySelector('link[href$="assets/css/site.css"], link[href*="/assets/css/site.css"]');
  const assetBase = stylesheetNode ? new URL("./", stylesheetNode.href) : null;

  document.querySelectorAll(".media").forEach((node) => {
    if (node.dataset.mediaInit === "1") return;
    node.dataset.mediaInit = "1";
    buildFallbackLabel(node);

    const imageUrl = getComputedStyle(node).getPropertyValue("--media-image").trim();
    const match = imageUrl.match(/^url\((['"]?)(.+?)\1\)$/);
    if (!match || !match[2]) return;

    let resolvedSrc = match[2];
    try {
      resolvedSrc = assetBase ? new URL(match[2], assetBase).href : match[2];
    } catch (error) {
      resolvedSrc = match[2];
    }

    const img = document.createElement("img");
    img.className = "media-img";
    img.alt = "";
    img.loading = "lazy";
    img.decoding = "async";
    img.src = resolvedSrc;

    img.addEventListener("load", () => {
      node.classList.add("media-ready");
    }, { once: true });

    img.addEventListener("error", () => {
      img.remove();
    }, { once: true });

    node.insertBefore(img, node.firstChild);
  });
}

async function loadIncludes() {
  return Promise.resolve();
}

window.initSiteUI = () => {
  bindNavToggles();
  bindFaqs();
  initTypedText();
  initMediaBlocks();
};

window.loadTransyesComponents = async ({
  header,
  footer,
  siteRoot = "",
  fallbackHeaderId,
  fallbackFooterId
}) => {
  const normalizeSiteRoot = (value) => {
    if (!value) return "";
    const trimmed = value.endsWith("/") ? value.slice(0, -1) : value;
    return trimmed === "/" ? "" : trimmed;
  };

  const rewriteComponentUrls = (target, rootPath) => {
    const normalizedRoot = normalizeSiteRoot(rootPath);
    if (!normalizedRoot) return;

    target.querySelectorAll("[href],[src]").forEach((node) => {
      ["href", "src"].forEach((attr) => {
        const value = node.getAttribute(attr);
        if (!value || !value.startsWith("/") || value.startsWith("//")) return;
        node.setAttribute(attr, `${normalizedRoot}${value}`);
      });
    });
  };

  const injectComponent = async (targetId, src, fallbackId) => {
    const target = document.getElementById(targetId);
    if (!target) return;

    if (window.location.protocol === "file:") {
      const fallback = fallbackId
        ? document.getElementById(fallbackId)
        : null;
      if (fallback) {
        target.innerHTML = fallback.innerHTML;
      }
      return;
    }

    try {
      const response = await fetch(src);
      if (!response.ok) throw new Error(`Failed to load ${src}`);
      const buffer = await response.arrayBuffer();
      const html = new TextDecoder("utf-8").decode(buffer);
      target.innerHTML = html;
      rewriteComponentUrls(target, siteRoot);
    } catch (error) {
      const fallback = fallbackId
        ? document.getElementById(fallbackId)
        : null;
      if (fallback) {
        target.innerHTML = fallback.innerHTML;
      } else {
        console.error(error);
      }
    }
  };

  await Promise.all([
    injectComponent("site-header", header, fallbackHeaderId),
    injectComponent("site-footer", footer, fallbackFooterId)
  ]);
  window.initSiteUI();
};

document.addEventListener("DOMContentLoaded", async () => {
  await loadIncludes();
  window.initSiteUI();
});
