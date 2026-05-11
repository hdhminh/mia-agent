export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const id = url.pathname.replace(/^\/+/, '').trim();

    if (!id) {
      return new Response('Short link id missing', { status: 400 });
    }

    if (!/^[a-zA-Z0-9_-]{4,32}$/.test(id)) {
      return new Response('Invalid short link id', { status: 400 });
    }

    const backendBase =
      (env && env.SHORTLINK_BACKEND_URL) ||
      'https://n8n.huynhminh.com/webhook/shortlink/go';

    const target = `${backendBase}?id=${encodeURIComponent(id)}`;

    return fetch(target, {
      method: 'GET',
      headers: {
        'User-Agent': request.headers.get('User-Agent') || '',
      },
      redirect: 'manual',
    });
  },
};
