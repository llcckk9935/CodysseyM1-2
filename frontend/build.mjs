import {mkdir,copyFile,writeFile} from 'node:fs/promises';
const raw = process.env.API_BASE_URL;
if (!raw) throw new Error('API_BASE_URL is required');
const url = new URL(raw);
if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) throw new Error('Invalid API_BASE_URL');
await mkdir('dist', {recursive:true});
for (const name of ['index.html','styles.css','app.js']) await copyFile(name,`dist/${name}`);
await writeFile('dist/config.js',`window.APP_CONFIG = ${JSON.stringify({API_BASE_URL:raw.replace(/\/$/,'')})};\n`);
