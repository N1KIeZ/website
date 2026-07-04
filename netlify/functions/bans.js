const BANS_KEY = 'banned_keys';

exports.handler = async (event, context) => {
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
    'Content-Type': 'application/json',
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }

  const store = context.netlify?.blobs?.getStore('bans');
  if (!store) {
    return { statusCode: 500, headers, body: JSON.stringify({ error: 'Netlify Blobs not configured' }) };
  }

  try {
    if (event.httpMethod === 'GET') {
      const data = await store.get(BANS_KEY, { type: 'json' });
      const bans = data?.banned || [];
      return { statusCode: 200, headers, body: JSON.stringify({ banned: bans }) };
    }

    if (event.httpMethod === 'POST') {
      const { key, action } = JSON.parse(event.body || '{}');
      if (!key) {
        return { statusCode: 400, headers, body: JSON.stringify({ error: 'key required' }) };
      }

      const data = await store.get(BANS_KEY, { type: 'json' });
      let bans = data?.banned || [];

      if (action === 'ban') {
        if (!bans.includes(key)) {
          bans.push(key);
        }
      } else if (action === 'unban') {
        bans = bans.filter(k => k !== key);
      } else {
        return { statusCode: 400, headers, body: JSON.stringify({ error: 'action must be ban or unban' }) };
      }

      await store.set(BANS_KEY, JSON.stringify({ banned: bans }), { type: 'json' });
      return { statusCode: 200, headers, body: JSON.stringify({ success: true, banned: bans }) };
    }

    if (event.httpMethod === 'DELETE') {
      const { key } = JSON.parse(event.body || '{}');
      if (!key) {
        return { statusCode: 400, headers, body: JSON.stringify({ error: 'key required' }) };
      }

      const data = await store.get(BANS_KEY, { type: 'json' });
      let bans = data?.banned || [];
      bans = bans.filter(k => k !== key);
      await store.set(BANS_KEY, JSON.stringify({ banned: bans }), { type: 'json' });
      return { statusCode: 200, headers, body: JSON.stringify({ success: true, banned: bans }) };
    }

    return { statusCode: 405, headers, body: JSON.stringify({ error: 'method not allowed' }) };
  } catch (err) {
    console.error('Bans function error:', err);
    return { statusCode: 500, headers, body: JSON.stringify({ error: 'internal error' }) };
  }
};