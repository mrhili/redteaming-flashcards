
class Card {
  constructor(obj){
    Object.assign(this, obj);
  }
}

class Deck {
  constructor(cards){
    this.cards = cards.map(c => new Card(c));
    this.index = 0;
    this.order = _.range(this.cards.length);
  }

  shuffle(){
    this.order = _.shuffle(this.order);
    this.index = 0;
  }

  get current(){
    if(this.order.length===0) return null;
    return this.cards[this.order[this.index]];
  }

  next(){
    if(this.order.length===0) return null;
    this.index = (this.index+1) % this.order.length;
    return this.current;
  }

  prev(){
    if(this.order.length===0) return null;
    this.index = (this.index-1 + this.order.length) % this.order.length;
    return this.current;
  }
}

class Storage {
  constructor(){
    this.store = localforage.createInstance({name:'rt-flashcards'});
    this.key = 'user_labels_v1';
  }
  async saveLabels(labels){
    await this.store.setItem(this.key, labels);
  }
  async loadLabels(){
    return (await this.store.getItem(this.key)) || {};
  }
  async clear(){ await this.store.removeItem(this.key); }
}

class App {
  constructor(){
    this.storage = new Storage();
    this.deck = null;
    this.labels = {}; // per-card metadata user edits
    this.ui = {};
    this._bindElements();
    this._bindShortcuts();
    this.init();
  }

  _bindElements(){
    this.ui.question = document.getElementById('question');
    this.ui.hints = document.getElementById('hints');
    this.ui.flashcard = document.getElementById('flashcard');
    this.ui.prev = document.getElementById('prev');
    this.ui.next = document.getElementById('next');
    this.ui.flip = document.getElementById('flip');
    this.ui.shuffle = document.getElementById('shuffle');
    this.ui.export = document.getElementById('export');
    this.ui.importBtn = document.getElementById('import');
    this.ui.importFile = document.getElementById('import-file');
    this.ui.search = document.getElementById('search');
    this.ui.filterCategory = document.getElementById('filter-category');
    this.ui.filterDifficulty = document.getElementById('filter-difficulty');
    this.ui.filterUsefulness = document.getElementById('filter-usefulness');
    this.ui.categoriesList = document.getElementById('categories-list');
    this.ui.stats = document.getElementById('stats');
    this.ui.toggleGrasped = document.getElementById('toggle-grasped');
    this.ui.difficultyBtns = Array.from(document.querySelectorAll('.difficulty'));
    this.ui.usefulnessSelect = document.getElementById('usefulness-select');

    this.ui.prev.addEventListener('click', ()=>this.showPrev());
    this.ui.next.addEventListener('click', ()=>this.showNext());
    this.ui.flip.addEventListener('click', ()=>this.flip());
    this.ui.shuffle.addEventListener('click', ()=>this.shuffle());
    this.ui.export.addEventListener('click', ()=>this.exportData());
    this.ui.importBtn.addEventListener('click', ()=>this.ui.importFile.click());
    this.ui.importFile.addEventListener('change', e=>this.handleImport(e));
    this.ui.search.addEventListener('input', _.debounce(()=>this.applyFilters(),250));
    this.ui.filterCategory.addEventListener('change', ()=>this.applyFilters());
    this.ui.filterDifficulty.addEventListener('change', ()=>this.applyFilters());
    this.ui.filterUsefulness.addEventListener('change', ()=>this.applyFilters());
    this.ui.toggleGrasped.addEventListener('click', ()=>this.toggleGrasped());
    this.ui.difficultyBtns.forEach(b=>b.addEventListener('click', e=>this.setDifficulty(e.target.dataset.diff)));
    this.ui.usefulnessSelect.addEventListener('change', ()=>this.setUsefulness(this.ui.usefulnessSelect.value));
    this.ui.flashcard.addEventListener('click', ()=>this.flip());
  }

  _bindShortcuts(){
    document.addEventListener('keydown', (e)=>{
      if(e.target.tagName==='INPUT' || e.target.tagName==='SELECT') return;
      if(e.key==='f' || e.key==='F') this.flip();
      if(e.key==='n' || e.key==='N') this.showNext();
      if(e.key==='p' || e.key==='P') this.showPrev();
      if(e.key==='1') this.setDifficulty('easy');
      if(e.key==='2') this.setDifficulty('medium');
      if(e.key==='3') this.setDifficulty('hard');
      if(e.key==='g' || e.key==='G') this.toggleGrasped();
      if(e.key==='u' || e.key==='U') this.cycleUsefulness();
    });
  }

  async init(){
    try{
      const res = await fetch('cards.json');
      const arr = await res.json();
      this.deck = new Deck(arr);
      this._populateFilters(arr);
      this.labels = await this.storage.loadLabels();
      this.applyFilters();
      this.renderStats();
      this.showCurrent();
    }catch(err){
      console.error('Failed to load cards.json', err);
      this.ui.question.textContent = 'Failed to load cards.json — check console.';
    }
  }

  _populateFilters(arr){
    const catSet = new Set();
    arr.forEach(c=> (c.categories||[]).forEach(x=>catSet.add(x)));
    const frag = document.createDocumentFragment();
    [...catSet].sort().forEach(cat=>{
      const opt = document.createElement('option'); opt.value=cat; opt.textContent=cat; this.ui.filterCategory.appendChild(opt);
      const li = document.createElement('li'); li.textContent = cat; this.ui.categoriesList.appendChild(li);
    });
  }

  applyFilters(){
    const q = this.ui.search.value.trim().toLowerCase();
    const cat = this.ui.filterCategory.value;
    const diff = this.ui.filterDifficulty.value;
    const use = this.ui.filterUsefulness.value;
    let list = this.deck.cards.filter(c=>{
      if(q){
        const hay = (c.question + ' ' + (c.categories||[]).join(' ') + ' ' + (c.answer||'')).toLowerCase();
        if(!hay.includes(q)) return false;
      }
      if(cat && !(c.categories||[]).includes(cat)) return false;
      if(diff && c.difficulty!==diff) return false;
      if(use && c.usefulness!==use) return false;
      return true;
    });
    // rebuild deck.order
    this.deck.order = list.map(c=>this.deck.cards.indexOf(c));
    if(this.deck.order.length===0){ this.ui.question.textContent='No cards match filters.'; return; }
    this.deck.index = 0;
    this.showCurrent();
  }

  showCurrent(){
    const cur = this.deck.current;
    if(!cur) return;
    this._renderCardFront(cur);
    this._applyLabelsToUI(cur.id);
  }

  showNext(){ this.deck.next(); this.showCurrent(); }
  showPrev(){ this.deck.prev(); this.showCurrent(); }

  _renderCardFront(card){
    this.ui.flashcard.classList.remove('back');
    this.ui.flashcard.classList.add('front');
    this.ui.question.textContent = card.question;
    this.ui.hints.innerHTML = card.hints ? card.hints.map(h=>`<div>• ${h}</div>`).join('') : '';
  }

  _renderCardBack(card){
    this.ui.flashcard.classList.remove('front');
    this.ui.flashcard.classList.add('back');
    this.ui.question.textContent = card.answer;
    this.ui.hints.innerHTML = `<div class="meta">Categories: ${(card.categories||[]).join(', ')}</div>`;
  }

  flip(){
    const c = this.deck.current; if(!c) return;
    if(this.ui.flashcard.classList.contains('front')) this._renderCardBack(c); else this._renderCardFront(c);
  }

  async toggleGrasped(){
    const c = this.deck.current; if(!c) return;
    const id = c.id;
    const cur = (this.labels[id] && this.labels[id].grasped) ? true : false;
    this.labels[id] = {...this.labels[id], grasped: !cur};
    await this.storage.saveLabels(this.labels);
    this._applyLabelsToUI(id);
    this.renderStats();
  }

  async setDifficulty(diff){
    const c = this.deck.current; if(!c) return;
    const id = c.id; this.labels[id] = {...this.labels[id], difficulty: diff};
    await this.storage.saveLabels(this.labels);
    this._applyLabelsToUI(id);
    this.renderStats();
  }

  async setUsefulness(val){
    const c = this.deck.current; if(!c) return;
    const id = c.id; this.labels[id] = {...this.labels[id], usefulness: val};
    await this.storage.saveLabels(this.labels);
    this._applyLabelsToUI(id);
    this.renderStats();
  }

  async cycleUsefulness(){
    const c = this.deck.current; if(!c) return;
    const opts = ['useful','dangerous','information'];
    const id = c.id; const cur = (this.labels[id] && this.labels[id].usefulness) || c.usefulness || 'useful';
    const i = (opts.indexOf(cur)+1) % opts.length; await this.setUsefulness(opts[i]);
  }

  _applyLabelsToUI(id){
    const lab = this.labels[id] || {};
    // difficulty
    this.ui.difficultyBtns.forEach(b=>b.classList.toggle('active', b.dataset.diff=== (lab.difficulty || this.deck.current.difficulty)));
    // grasped
    this.ui.toggleGrasped.textContent = (lab.grasped) ? 'Grasped ✓' : 'Toggle (G)';
    // usefulness
    this.ui.usefulnessSelect.value = lab.usefulness || this.deck.current.usefulness || 'useful';
  }

  renderStats(){
    const total = this.deck.cards.length;
    const grasped = Object.values(this.labels).filter(x=>x.grasped).length;
    this.ui.stats.innerHTML = `Cards: ${total}<br/>Grasped: ${grasped}`;
  }

  shuffle(){ this.deck.shuffle(); this.showCurrent(); }

  exportData(){
    const payload = {
      dataset: this.deck.cards,
      labels: this.labels
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {type:'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href=url; a.download='flashcards-export.json'; a.click();
    URL.revokeObjectURL(url);
  }

  handleImport(evt){
    const f = evt.target.files[0]; if(!f) return;
    const reader = new FileReader();
    reader.onload = async (e)=>{
      try{
        const obj = JSON.parse(e.target.result);
        if(Array.isArray(obj)){
          // assume it's an array of cards
          this.deck = new Deck(obj);
        }else if(obj.dataset && obj.labels){
          this.deck = new Deck(obj.dataset);
          this.labels = obj.labels;
          await this.storage.saveLabels(this.labels);
        }else{ alert('Unknown JSON structure.'); return; }
        this._populateFilters(this.deck.cards);
        this.applyFilters();
        this.renderStats();
      }catch(err){ alert('Invalid JSON'); }
    };
    reader.readAsText(f);
  }
}

// bootstrap
window.addEventListener('DOMContentLoaded', ()=>{
  new App();
});
