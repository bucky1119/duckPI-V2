// Unit-level UI checks with a minimal DOM, without a browser dependency.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),elements=new Map();
class Element{
 constructor(tag){this.tagName=tag;this.children=[];this.value='';this.textContent='';this.classList={toggle(){}};this.attributes={};this.style={};}
 set id(id){this._id=id;elements.set(id,this);}get id(){return this._id;}
 append(...nodes){this.children.push(...nodes);}appendChild(node){this.append(node);return node;}
 replaceChildren(...nodes){this.children=nodes;}setAttribute(k,v){this.attributes[k]=v;}
}
const html=fs.readFileSync(path.join(root,'web/index.html'),'utf8');
for(const match of html.matchAll(/id="([^"]+)"/g)){const e=new Element('div');e.id=match[1];}
elements.get('filter').value='all';
const context=vm.createContext({document:{getElementById:id=>elements.get(id),createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag)},location:{protocol:'http:'},lastDownload:null,console,Date,URL,Blob,setTimeout});
vm.runInContext(html.split('<script>')[1].split('</script>')[0],context);
context.fixture=JSON.parse(fs.readFileSync(path.join(root,'tests/fixtures/synthetic/pedigree.tsv.review.json'),'utf8'));
vm.runInContext('load(fixture); download=(name,text,type)=>{lastDownload={name,text,type};};',context);
assert.equal(elements.get('candidate-rows').children.length,5);
elements.get('filter').value='ambiguous';vm.runInContext('renderRows()',context);assert.equal(elements.get('candidate-rows').children.length,2);
vm.runInContext("choose(report.candidatePairs.find(c=>c.parent==='SIRE_A'&&c.child==='OFFSPRING_2'))",context);
function save(status,note){elements.get('decision').value=status;elements.get('notes').value=note;elements.get('detail').children.find(e=>e.tagName==='button').onclick();}
save('accepted','');assert.match(elements.get('message').textContent,/Add a review reason/);
save('accepted','Synthetic test: reviewed supporting records.');
vm.runInContext("choose(report.candidatePairs.find(c=>c.parent==='SIRE_B'))",context);
save('accepted','Synthetic test: second candidate.');assert.match(elements.get('message').textContent,/already accepted/);
elements.get('export-reviewed').onclick();assert.match(vm.runInContext('lastDownload.text',context),/OFFSPRING_2\tSIRE_A\t\tmanually_accepted/);
elements.get('export-pedigree').onclick();let inferred=vm.runInContext('lastDownload.text',context);
assert.match(inferred,/OFFSPRING_2\t\tDAM_A\tambiguous/);assert.match(inferred,/OFFSPRING_1\tSIRE_A\t\tunique_inferred/);
elements.get('export-json').onclick();context.saved=JSON.parse(vm.runInContext('lastDownload.text',context));vm.runInContext('load(saved)',context);
assert.equal(vm.runInContext("Object.values(decisions).filter(d=>d.status==='accepted').length",context),1);
elements.get('export-candidates').onclick();assert.match(vm.runInContext('lastDownload.text',context),/Synthetic test: reviewed supporting records/);
context.cell='line1\nline2\tquote"';assert.equal(vm.runInContext('tsv([{value:cell}],["value"])',context),'value\n"line1\nline2\tquote"""\n');
context.empty=JSON.parse(JSON.stringify(context.fixture));context.empty.candidatePairs=[];context.empty.summary.candidateLinks=0;vm.runInContext('load(empty)',context);assert.match(elements.get('detail').textContent,/Select a candidate row/);
context.study=JSON.parse(fs.readFileSync(path.join(root,'example_data/results/king_pedigree.tsv.review.json'),'utf8'));vm.runInContext('load(study)',context);assert.equal(vm.runInContext('selected.parent',context),'NKX06X40X26603');assert.equal(elements.get('family-id').textContent,'NKX06X41X13476');
elements.get('family-scope').value='context';elements.get('family-scope').onchange();assert.ok(parseInt(elements.get('pedigree').style.minWidth)>1000);elements.get('family-scope').value='parents';elements.get('family-scope').onchange();assert.equal(elements.get('pedigree').style.minWidth,'600px');
console.log('UI unit checks passed: filters, required notes, competing acceptance prevention, separate inferred/reviewed exports, JSON decision roundtrip and TSV escaping.');
