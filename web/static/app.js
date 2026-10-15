const $ = (id) => document.getElementById(id);
let experiments = [];
const fmt = (v, suffix='') => v == null ? '—' : `${Number(v).toLocaleString(undefined,{maximumFractionDigits:2})}${suffix}`;
const escapeHtml = (v) => String(v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function renderBars(target, metric, suffix='') {
  const el = $(target);
  if (!window.selectedExperiment) { el.innerHTML = '<span class="empty-row">Run a simulation to view metrics</span>'; return; }
  const m = window.selectedExperiment.metrics;
  if (!m || !m.tcp || !m.udp) { el.textContent = 'Metrics unavailable'; return; }
  const vals = [m.tcp[metric],m.udp[metric]];
  const max = Math.max(...vals.map(x => Number(x)||0), 1);
  el.innerHTML = ['tcp','udp'].map((flow,i) => `<div class="bar-row"><span class="bar-label">${flow.toUpperCase()}</span><div class="bar-track"><div class="bar-fill ${flow}" style="width:${Math.max(0,(Number(vals[i])||0)/max*100)}%"></div></div><span class="bar-value">${fmt(vals[i],suffix)}</span></div>`).join('');
}
function showExperiment(index) {
  const e = experiments[index];
  if (e && (!e.metrics || !e.metrics.tcp || !e.metrics.udp)) throw Error('Experiment data is missing TCP/UDP metrics');
  window.selectedExperiment = e;
  const modelLabel = $('modelLabel');
  if (modelLabel) modelLabel.textContent = e ? ` · ${e.model || e.engine || 'unknown model'}` : ''; 
  $('snapshotLabel').textContent = e ? `${e.scenario} · ${e.loss_percent}% loss · ${e.delay_ms}ms delay` : 'No data yet';
  for (const [id,flow,key,suffix] of [['tcpThroughput','tcp','throughput_kbps',''],['udpThroughput','udp','throughput_kbps',''],['tcpDelivery','tcp','delivery_ratio_percent','%'],['udpDelivery','udp','delivery_ratio_percent','%']]) $(''+id).textContent = e ? fmt(e.metrics[flow][key],suffix) : '—';
  renderBars('throughputChart','throughput_kbps'); renderBars('delayChart','average_delay_ms');
  renderBars('deliveryChart','delivery_ratio_percent','%'); renderBars('lossChart','unreceived_packets');
}
async function refresh(preferred) {
  const r = await fetch('/api/results');
  if (!r.ok) throw Error('Could not fetch results');
  experiments = await r.json();
  const select = $('scenarioSelect');
  select.innerHTML = experiments.length ? experiments.map((e,i)=>`<option value="${i}">${escapeHtml(e.scenario)}</option>`).join('') : '<option value="">No experiments yet</option>';
  let index = experiments.findIndex(e=>e.scenario===preferred);
  if (index < 0) index = experiments.length-1;
  select.value = index >= 0 ? String(index) : '';
  showExperiment(index);
  $('experimentRows').innerHTML = experiments.length ? experiments.slice().reverse().map(e => `<tr><td>${escapeHtml(e.scenario)}</td><td>${fmt(e.loss_percent)}%</td><td>${fmt(e.delay_ms)} ms</td><td>${fmt(e.queue_packets)}</td><td>${fmt(e.metrics.tcp.throughput_kbps)}</td><td>${fmt(e.metrics.udp.throughput_kbps)}</td><td><span class="ok-pill">● Complete</span></td></tr>`).join('') : '<tr><td colspan="7" class="empty-row">No experiments yet. Run your first simulation above.</td></tr>';
}
function setBusy(busy, message, error=false){$('runBtn').disabled=busy;$('batchBtn').disabled=busy;$('message').textContent=message;$('message').className=error?'form-message error':'form-message';}
async function execute(url,body){setBusy(true,'Running simulation — this may take a moment…');try{const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await r.json();if(!r.ok)throw Error(data.error||'Simulation failed');await refresh(Array.isArray(data)?'baseline':data.scenario);setBusy(false,'✓ Simulation complete. Results saved.');}catch(e){setBusy(false,e.message || String(e),true);}}
$('simForm').addEventListener('submit',e=>{e.preventDefault();execute('/api/run',{loss:Number($('loss').value),delay:Number($('delay').value),queue:Number($('queue').value),seed:Number($('seed').value),corruption:Number($('corruption').value),duplication:Number($('duplication').value),reordering:Number($('reordering').value),engine:$('engine').value});});
$('batchBtn').addEventListener('click',()=>execute('/api/run-all',{engine:$('engine').value}));
$('scenarioSelect').addEventListener('change',e=>showExperiment(Number(e.target.value)));
for(const id of ['loss','delay','corruption','duplication','reordering'])$(id).addEventListener('input',()=>{$(id+'Label').textContent=$(id).value+(id==='delay'?' ms':'%');});
refresh().catch(e=>setBusy(false,e.message,true));
