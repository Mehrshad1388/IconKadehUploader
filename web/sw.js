// این یک سرویس ورکر ساده برای فعال کردن قابلیت PWA است.
self.addEventListener('install', event => {
  console.log('Service worker installing...');
});

self.addEventListener('fetch', event => {
  // در حال حاضر درخواست‌ها را مستقیماً به شبکه ارسال می‌کنیم.
  event.respondWith(fetch(event.request));
});
