'use strict';
const fs=require('node:fs'),path=require('node:path'),{validateSummary}=require('../docs/ceb/v3/report-validator.js');
const root=path.resolve(__dirname,'..'),file=path.join(root,'docs/ceb/v3/runs.json'),manifest=JSON.parse(fs.readFileSync(path.join(root,'docs/ceb/v3/manifest.json'),'utf8')),raw=JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH,'utf8')).inputs?.run_json;
if(typeof raw!=='string'||raw.length>60000)throw Error('run_json <=60000');
const r=validateSummary(JSON.parse(raw),manifest),db=JSON.parse(fs.readFileSync(file,'utf8'));
if(db.suite_version!==manifest.version||!Array.isArray(db.runs)||db.runs.some(x=>x.run_id===r.run_id))throw Error('Registry/version/duplicate run_id');
db.runs.push(r);fs.writeFileSync(file,JSON.stringify(db,null,2)+'\n');console.log('Accepted format only: '+r.run_id);
