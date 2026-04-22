const live2dPath = 'https://fastly.jsdelivr.net/npm/live2d-widgets@1.0.0/dist/';

let imageOverridden = false;
let loadingPromise: Promise<void> | null = null;
let initialized = false;

function overrideImage() {
  if (imageOverridden) return;
  imageOverridden = true;
  const OriginalImage = window.Image;
  // @ts-expect-error override Image for CORS
  window.Image = function (...args: ConstructorParameters<typeof Image>) {
    const img = new OriginalImage(...args);
    img.crossOrigin = 'anonymous';
    return img;
  };
  window.Image.prototype = OriginalImage.prototype;
}

function loadResource(url: string, type: 'css' | 'js') {
  return new Promise<void>((resolve, reject) => {
    let el: HTMLElement;
    if (type === 'css') {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = url;
      el = link;
    } else {
      const script = document.createElement('script');
      script.type = 'module';
      script.src = url;
      el = script;
    }
    el.onload = () => resolve();
    el.onerror = () => reject();
    document.head.appendChild(el);
  });
}

function ensureLoaded(): Promise<void> {
  if (loadingPromise) return loadingPromise;
  overrideImage();
  loadingPromise = Promise.all([
    loadResource(live2dPath + 'waifu.css', 'css'),
    loadResource(live2dPath + 'waifu-tips.js', 'js'),
  ]).then(() => undefined);
  return loadingPromise;
}

export async function enableLive2d() {
  await ensureLoaded();
  const el = document.getElementById('waifu');
  if (el) {
    el.style.display = '';
    return;
  }
  if (!initialized) {
    initialized = true;
    (window as unknown as { initWidget: (opts: Record<string, unknown>) => void }).initWidget({
      waifuPath: live2dPath + 'waifu-tips.json',
      cubism2Path: live2dPath + 'live2d.min.js',
      cubism5Path: 'https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js',
      tools: ['hitokoto', 'asteroids', 'switch-model', 'switch-texture', 'photo', 'info', 'quit'],
      modelId: 1,
      drag: false,
    });
  }
}

export function disableLive2d() {
  const el = document.getElementById('waifu');
  if (el) el.style.display = 'none';
}
