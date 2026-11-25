'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {validate}=require('../docs/ceb/v2/import-validator.js');
const root=path.resolve(__dirname,'..'),mp=path.join(root,'docs/ceb/tasks.json'),rp=path.join(root,'docs/ceb/v2/runs.json');
const bytes=fs.readFileSync(mp),manifest=JSON.parse(bytes),blob=crypto.createHash('sha1').update('blob '+bytes.length+'\0').update(bytes).digest('hex');
const event=JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH,'utf8')),raw=event.inputs?.run_json;
if(typeof raw!=='string'||raw.length>60000)throw Error('run_json must be at most 60000 characters');
const run=JSON.parse(raw),check=validate(run,manifest,blob);if(!check.ok){console.error(check.errors.slice(0,30).join('\n'));process.exit(1)}
const registry=JSON.parse(fs.readFileSync(rp,'utf8'));
if(registry.suite_version!==manifest.version||!Array.isArray(registry.runs))throw Error('Registry version mismatch');
if(registry.runs.some(r=>r.run_id===run.run_id))throw Error('Duplicate run_id: '+run.run_id);
registry.runs.push({...run,publication:{source:'owner_workflow',received_at:new Date().toISOString(),validation:'format_only'},quality_score_100:null,critical_failures:null});
fs.writeFileSync(rp,JSON.stringify(registry,null,2)+'\n');console.log('Accepted '+run.run_id+'; format only, '+check.completed+' completed tasks.');
