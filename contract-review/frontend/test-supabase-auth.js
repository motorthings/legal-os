const fetch = require('node-fetch');

const SUPABASE_URL = 'https://kwxngptwzllzlifpwvns.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt3eG5ncHR3emxsemxpZnB3dm5zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ4ODQxNTEsImV4cCI6MjA4MDQ2MDE1MX0.AHAPcQsSqHt8gNkTcs5mgo-Uo0r9uPsu2fSonhNgqUY';

async function testAuth() {
  try {
    const response = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': SUPABASE_ANON_KEY,
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
      },
      body: JSON.stringify({
        email: 'charlie@waifinder.org',
        password: 'ButtButt'
      })
    });

    const data = await response.json();
    console.log('Status:', response.status);
    console.log('Response:', JSON.stringify(data, null, 2));
  } catch (error) {
    console.error('Error:', error.message);
  }
}

testAuth();
