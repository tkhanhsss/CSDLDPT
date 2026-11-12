// Exercise the actual generated form scripts without touching submitted grades.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');

(async () => {
  for (const role of ['A', 'B']) {
    const html = fs.readFileSync(`gd2/evaluation/p6/reviewer_${role}.html`, 'utf8');
    const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
    const ids = [...html.matchAll(/<section data-pair="(P\d+)"/g)].map(m => m[1]);
    assert.equal(new Set(ids).size, 36);
    const fields = ['grade', 'query_evidence', 'document_evidence', 'reason'];
    const rows = ids.map((id, i) => ({dataset: {pair: id}, cells: Object.fromEntries(fields.map(f =>
      [f, {value: f === 'grade' ? (i === 35 ? '' : String(i % 3)) : `${f}: tiếng Việt, "quote"\nline two`}])) ,
      querySelector(name) { return this.cells[name.slice(1)]; }}));
    const reviewer = {value: `Thành viên ${role}`}, status = {}, restore = {};
    let blob, filename, clicked = false;
    const context = {
      Blob, setTimeout: fn => fn(), alert: message => { throw Error(message); },
      URL: {createObjectURL: value => {blob = value; return 'blob:test';}, revokeObjectURL: () => {}},
      document: {querySelectorAll: () => rows,
        getElementById: id => ({reviewer, status, restore}[id]),
        createElement: () => ({set href(value) {}, set download(value) {filename = value;}, click() {clicked = true;}})}
    };
    vm.runInNewContext(script, context);
    vm.runInNewContext('saveCSV()', context);
    assert.ok(clicked);
    assert.equal(filename, `reviewer_${role}.csv`);
    const csv = await blob.text();
    assert.ok(csv.includes('tiếng Việt'));
    const original = rows.map(row => fields.map(f => row.cells[f].value));
    rows.forEach(row => fields.forEach(f => row.cells[f].value = ''));
    reviewer.value = '';
    await restore.onchange({target: {files: [{text: async () => csv}]}});
    assert.deepEqual(rows.map(row => fields.map(f => row.cells[f].value)), original);
    assert.equal(reviewer.value, `Thành viên ${role}`);
    console.log(`Form ${role}: 36 IDs, export/import, Unicode, commas, quotes, multiline and pending grades passed`);
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
