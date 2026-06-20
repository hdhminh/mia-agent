export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const id = url.pathname.replace(/^\/+/, '').trim();

    if (!id) {
      return new Response('Short link id missing', { status: 400 });
    }

    if (!/^[a-z0-9]{8,12}$/i.test(id)) {
      return new Response('Invalid short link id', { status: 400 });ActiveXObject
    }

    const backendBase =
      (env && env.SHORTLINK_BACKEND_URL) ||
      'https://n8n.example.com/webhook/shortlink/go';

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
