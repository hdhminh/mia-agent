const http = require('http');
const fs = require('fs');
const path = require('path');

const API_KEY = process.env.N8N_API_KEY || '';
const GMAIL_DIR = '/tmp/gmail_workflows';

function apiRequest(method, urlPath, data) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'localhost',
      port: 5678,
      path: urlPath,
      method: method,
      headers: {
        'Content-Type': 'application/json',
        'X-N8N-API-KEY': API_KEY
      }
    };
    const req = http.request(options, (res) => {
      let body = '';
      res.on('data', c => body += c);
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, data: JSON.parse(body) });
        } catch(e) {
          resolve({ status: res.statusCode, data: body });
        }
      });
    });
    req.on('error', reject);
    if (data) req.write(typeof data === 'string' ? data : JSON.stringify(data));
    req.end();
  });
}

async function findWorkflow(name) {
  const encoded = encodeURIComponent(name);
  const res = await apiRequest('GET', `/api/v1/workflows?limit=250&name=${encoded}`);
  if (res.status !== 200) return null;
  const workflows = res.data?.data || [];
  for (const w of workflows) {
    if (w.name === name) return w.id;
  }
  return null;
}

async function deployWorkflow(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const workflow = JSON.parse(content);
  const name = workflow.name;
  console.log(`\n--- Deploying: ${name} ---`);

  // Ensure required fields for n8n API
  if (!workflow.settings) {
    workflow.settings = { executionOrder: 'v1' };
  }
  if (!workflow.staticData) {
    workflow.staticData = null;
  }

  const existingId = await findWorkflow(name);

  if (existingId) {
    console.log(`  Found existing ID: ${existingId} -> Updating...`);
    const updatePayload = { ...workflow };
    delete updatePayload.id; // Remove any id field
    const res = await apiRequest('PUT', `/api/v1/workflows/${existingId}`, updatePayload);
    console.log(`  Update status: ${res.status}`);
    if (res.status !== 200) console.log(`  Detail: ${JSON.stringify(res.data).substring(0, 300)}`);
    // Activate
    const act = await apiRequest('POST', `/api/v1/workflows/${existingId}/activate`);
    if (act.status !== 200) {
      // Try PATCH
      const act2 = await apiRequest('PATCH', `/api/v1/workflows/${existingId}`, { active: true });
      console.log(`  Activate status: ${act2.status}`);
    } else {
      console.log(`  Activated!`);
    }
    return existingId;
  } else {
    console.log('  Creating new workflow...');
    const createPayload = { ...workflow };
    // Remove node IDs that may conflict
    const res = await apiRequest('POST', '/api/v1/workflows', createPayload);
    if (res.status === 200 || res.status === 201) {
      const newId = res.data?.id || '';
      console.log(`  Created with ID: ${newId}`);
      if (newId) {
        const act = await apiRequest('POST', `/api/v1/workflows/${newId}/activate`);
        if (act.status !== 200) {
          const act2 = await apiRequest('PATCH', `/api/v1/workflows/${newId}`, { active: true });
          console.log(`  Activate status: ${act2.status}`);
        } else {
          console.log(`  Activated!`);
        }
      }
      return newId;
    } else {
      console.log(`  FAILED (${res.status}): ${JSON.stringify(res.data).substring(0, 300)}`);
      return null;
    }
  }
}

async function main() {
  console.log('='.repeat(50));
  console.log('Deploying Gmail Workflows to n8n');
  console.log('='.repeat(50));

  const files = fs.readdirSync(GMAIL_DIR).filter(f => f.endsWith('.json')).sort();
  // Deploy subs first, master last
  const subs = files.filter(f => !f.includes('master'));
  const masters = files.filter(f => f.includes('master'));

  console.log('\n=== Step 1: Deploy Gmail Sub-Workflows ===');
  for (const f of subs) {
    await deployWorkflow(path.join(GMAIL_DIR, f));
  }

  console.log('\n=== Step 2: Deploy Gmail Master ===');
  for (const f of masters) {
    await deployWorkflow(path.join(GMAIL_DIR, f));
  }

  // Update chatbot
  if (fs.existsSync('/tmp/chatbot.json')) {
    console.log('\n=== Step 3: Update Chatbot ===');
    await deployWorkflow('/tmp/chatbot.json');
  }

  console.log('\n' + '='.repeat(50));
  console.log('Done!');
}

main().catch(e => { console.error(e); process.exit(1); });
