/* A apresentação consulta a API; todas as operações são feitas nas árvores Python. */
"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const icon = (name) => `<svg class="icon" aria-hidden="true"><use href="#i-${name}"/></svg>`;
  const escape = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
  const number = (value, digits = 0) => Number(value ?? 0).toLocaleString("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  const normalize = (value) => String(value).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const formatDate = (value) => String(value).split("-").reverse().join("/");
  const keyLabel = (value) => `#${String(value).padStart(3, "0")}`;
  const PAGE_SIZE = 10;
  const app = { estado: null, tree: "AVL", view: "pacientes", traversal: "em_ordem", search: "", page: 1, pending: false, highlighted: null, detail: null, deleting: null, comparison: null, graphSignature: "", rootX: 0 };
  const views = {
    pacientes: ["Pacientes", "Cada cadastro no lugar certo. Cada árvore em equilíbrio."],
    arvores: ["Árvores", "Explore a estrutura real e acompanhe o que mantém tudo em equilíbrio."],
    comparativo: ["Comparativo", "Observe como AVL e Rubro-Negra respondem às mesmas operações."],
  };
  const scenarios = {
    A_insercao_crescente: "A · Inserção crescente",
    B_insercao_aleatoria: "B · Inserção aleatória",
    C_busca_existente: "C · Busca existente",
    C_busca_inexistente: "C · Busca inexistente",
    D_remocao_10: "D · Remoção de 10%",
    D_remocao_30: "D · Remoção de 30%",
    D_remocao_50: "D · Remoção de 50%",
  };

  // ============= CONEXÃO E ESTADO =================

  function connection(online) {
    $("connection-dot").style.background = online ? "#4ca28a" : "#c98763";
    $("connection-label").textContent = online ? "Execução local" : "Sem conexão";
    $("connection-error").hidden = online;
  }

  async function api(path, data) {
    let response;
    try {
      response = await fetch(path, data === undefined ? { cache: "no-store" } : {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data), cache: "no-store",
      });
    } catch {
      connection(false);
      throw new Error("Não foi possível conectar. Verifique se o servidor está em execução.");
    }
    const payload = await response.json();
    connection(true);
    if (!response.ok || !payload.ok) throw new Error(payload.erro || "Não foi possível concluir a operação.");
    if (payload.estado) {
      app.estado = payload.estado;
      render();
    }
    return payload;
  }

  async function perform(button, action, errorId) {
    if (app.pending) return;
    app.pending = true;
    const previousDisabled = button?.disabled ?? false;
    if (button) { button.disabled = true; button.classList.add("busy"); }
    $("conteudo").setAttribute("aria-busy", "true");
    if (errorId) $(errorId).hidden = true;
    try { await action(); }
    catch (error) {
      if (errorId && $(errorId).closest("dialog")?.open) {
        $(errorId).textContent = error.message;
        $(errorId).hidden = false;
      } else toast(error.message, true);
    } finally {
      app.pending = false;
      if (button) { button.disabled = previousDisabled; button.classList.remove("busy"); }
      $("conteudo").removeAttribute("aria-busy");
    }
  }

  function toast(message, error = false) {
    const element = document.createElement("div");
    element.className = `toast${error ? " error" : ""}`;
    element.innerHTML = `${icon(error ? "info" : "check")}<span>${escape(message)}</span><button class="icon-button" aria-label="Dispensar mensagem">${icon("close")}</button>`;
    element.querySelector("button").addEventListener("click", () => element.remove());
    $("toast-region").append(element);
    setTimeout(() => element.remove(), error ? 10000 : 6500);
  }

  function showView(view, updateHash = true) {
    if (!views[view]) view = "pacientes";
    const changed = app.view !== view;
    app.view = view;
    for (const name of Object.keys(views)) $(`view-${name}`).hidden = name !== view;
    document.querySelectorAll(".nav-item").forEach((button) => {
      const active = button.dataset.view === view;
      button.classList.toggle("active", active);
      if (active) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
    });
    $("page-title").textContent = views[view][0];
    $("page-description").textContent = views[view][1];
    $("breadcrumb-current").textContent = views[view][0];
    document.title = `Clínica — ${views[view][0]}`;
    if (updateHash) history.replaceState(null, "", `#${view}`);
    if (view === "arvores" && app.estado) renderTree();
    if (changed) window.scrollTo(0, 0);
  }

  function setTree(name) {
    if (!["AVL", "Rubro-Negra"].includes(name)) return;
    app.tree = name;
    app.highlighted = null;
    app.graphSignature = "";
    $("patient-tree-select").value = name;
    if (app.estado) renderTree();
  }

  function render() {
    if (!app.estado) return;
    const count = app.estado.pacientes.length;
    const avl = app.estado.arvores.AVL;
    const rn = app.estado.arvores["Rubro-Negra"];
    const valid = avl.valida && rn.valida;
    $("nav-count").textContent = number(count);
    $("patient-count").textContent = number(count);
    $("stat-count").textContent = number(count);
    $("stat-avl").innerHTML = `${number(avl.altura)}<small>${avl.altura === 1 ? "nível" : "níveis"}</small>`;
    $("stat-rn").innerHTML = `${number(rn.altura)}<small>${rn.altura === 1 ? "nível" : "níveis"}</small>`;
    $("stat-valid").textContent = valid ? "Tudo certo" : "Verificar";
    $("stat-valid").style.color = valid ? "#3d8472" : "#b94350";
    $("stat-valid-description").textContent = valid ? "Propriedades preservadas" : "Propriedade inválida detectada";
    $("summary-avl").textContent = `${avl.altura} ${avl.altura === 1 ? "nível" : "níveis"}`;
    $("summary-rn").textContent = `${rn.altura} ${rn.altura === 1 ? "nível" : "níveis"}`;
    renderPatients();
    renderMiniTree();
    renderLogs();
    if (app.view === "arvores") renderTree();
  }

  // ============= PACIENTES =================

  function renderPatients() {
    const all = app.estado.pacientes;
    const query = normalize(app.search.trim());
    const patients = query ? all.filter((p) => normalize(p.nome).includes(query) || String(p.prontuario).includes(query.replace(/^#/, ""))) : all;
    const pages = Math.max(1, Math.ceil(patients.length / PAGE_SIZE));
    app.page = Math.min(Math.max(1, app.page), pages);
    const start = (app.page - 1) * PAGE_SIZE;
    const palette = [["#edf2f8", "#7792aa"], ["#eaf4ef", "#6c9b86"], ["#f8efec", "#b48d7c"], ["#f0edf7", "#9585b0"], ["#eaf4f6", "#6f9aa7"]];
    $("patient-rows").innerHTML = patients.slice(start, start + PAGE_SIZE).map((patient) => {
      const fictitious = /\(Fictício\)$/i.test(patient.nome);
      const name = patient.nome.replace(/\s*\(Fictício\)$/i, "");
      const initials = name.trim().split(/\s+/).filter(Boolean).slice(0, 2).map((word) => word[0]).join("").toUpperCase();
      const [background, color] = palette[patient.prontuario % palette.length];
      return `<tr><td><div class="patient-name-cell"><span class="patient-avatar" style="background:${background};color:${color}" aria-hidden="true">${escape(initials)}</span><span><span class="patient-name" title="${escape(patient.nome)}">${escape(name)}</span><span class="patient-kind">${fictitious ? "Dados fictícios" : "Paciente cadastrado"}</span></span></div></td><td><span class="key-badge">${escape(keyLabel(patient.prontuario))}</span></td><td>${escape(formatDate(patient.data_nascimento))}</td><td>${escape(patient.telefone)}</td><td><div class="row-actions"><button class="icon-button" data-patient-detail="${patient.prontuario}" aria-label="Consultar ${escape(patient.nome)}" title="Consultar paciente">${icon("eye")}</button><button class="icon-button delete-action" data-patient-delete="${patient.prontuario}" aria-label="Remover ${escape(patient.nome)}" title="Remover paciente">${icon("trash")}</button></div></td></tr>`;
    }).join("");
    $("patients-empty").hidden = patients.length > 0;
    $("empty-title").textContent = all.length ? "Nenhum paciente encontrado" : "Seu primeiro cadastro começa aqui";
    $("empty-description").innerHTML = all.length ? "Tente outro nome ou número de prontuário." : "Adicione um paciente ou explore a interface<br>com uma pequena coleção de dados fictícios.";
    $("demo-button").hidden = all.length > 0 || query.length > 0;
    $("clear-search-button").hidden = !query;
    const noun = patients.length === 1 ? "paciente" : "pacientes";
    $("pagination-label").textContent = patients.length ? `${number(start + 1)}–${number(Math.min(start + PAGE_SIZE, patients.length))} de ${number(patients.length)} ${noun}${query ? (patients.length === 1 ? " encontrado" : " encontrados") : ""}` : (query ? "Nenhum resultado para esta busca" : "Nenhum paciente cadastrado");
    $("page-number").textContent = number(app.page);
    $("previous-page").disabled = app.page <= 1;
    $("next-page").disabled = app.page >= pages;
  }

  function openPatientForm() {
    $("patient-form").reset();
    $("patient-key").value = app.estado ? (app.estado.proximo_prontuario ?? "") : 1;
    $("patient-form-error").hidden = true;
    $("patient-dialog").showModal();
    $("patient-name").focus();
  }

  async function searchPatient(key, button) {
    if (!Number.isSafeInteger(key) || key <= 0) { toast("Informe um prontuário inteiro positivo.", true); return; }
    await perform(button, async () => {
      const response = await api("/api/buscar", { prontuario: key, arvore: app.tree });
      const result = response.resultado;
      app.highlighted = result.paciente ? key : null;
      if (result.paciente) {
        app.detail = result.paciente;
        $("detail-key").textContent = `Prontuário ${keyLabel(key)}`;
        $("detail-dialog-title").textContent = result.paciente.nome.replace(/\s*\(Fictício\)$/i, "");
        $("detail-content").innerHTML = `<div class="detail-fields"><div class="detail-field">${icon("calendar")}<div><span>Data de nascimento</span><strong>${escape(formatDate(result.paciente.data_nascimento))}</strong></div></div><div class="detail-field">${icon("phone")}<div><span>Telefone</span><strong>${escape(result.paciente.telefone)}</strong></div></div></div><div class="search-evidence">${icon("check")}<span>Encontrado na ${escape(result.arvore)} após visitar ${number(result.nos_visitados)} ${result.nos_visitados === 1 ? "nó" : "nós"}.</span></div>`;
        $("detail-dialog").showModal();
      } else toast(`Prontuário ${key} não encontrado na ${app.tree}. ${result.nos_visitados} nós visitados.`, true);
      if (app.view === "arvores") renderTree();
    });
  }

  function openDelete(key) {
    const patient = app.estado?.pacientes.find((item) => item.prontuario === key);
    if (!patient) return;
    app.deleting = key;
    $("delete-description").textContent = `${patient.nome} · prontuário ${keyLabel(key)}.`;
    $("delete-error").hidden = true;
    $("delete-dialog").showModal();
  }

  // ============= VISUALIZAÇÃO DAS ÁRVORES =================

  function graphLayout(root, gap = 62) {
    const nodes = [];
    const edges = [];
    let index = 0;
    function walk(node, depth) {
      if (!node) return null;
      const left = walk(node.esquerda, depth + 1);
      const entry = { key: node.chave, color: node.cor, x: 42 + index++ * gap, y: 42 + depth * 74, depth };
      nodes.push(entry);
      const right = walk(node.direita, depth + 1);
      if (left) edges.push([entry, left]);
      if (right) edges.push([entry, right]);
      return entry;
    }
    const top = walk(root, 0);
    return { nodes, edges, top, width: index * gap + 22, height: Math.max(320, ...nodes.map((node) => node.y + 55)) };
  }

  function searchPath(root, key) {
    const keys = new Set();
    let node = root;
    while (node && key !== null) {
      keys.add(node.chave);
      if (key === node.chave) break;
      node = key < node.chave ? node.esquerda : node.direita;
    }
    return keys;
  }

  function renderTree() {
    const tree = app.estado.arvores[app.tree];
    const rn = app.tree === "Rubro-Negra";
    document.querySelectorAll("[data-tree]").forEach((button) => {
      const active = button.dataset.tree === app.tree;
      button.classList.toggle("selected", active);
      button.setAttribute("aria-pressed", String(active));
    });
    $("tree-validation").classList.toggle("invalid", !tree.valida);
    $("tree-validation").innerHTML = `${icon(tree.valida ? "check" : "info")}${tree.valida ? "Propriedades válidas" : "Verifique as propriedades"}`;
    $("tree-caption-text").textContent = `Cada nó é um prontuário. Clique para consultar na ${app.tree}.`;
    $("tree-legend").innerHTML = rn ? '<span><i class="tree-dot black-dot"></i>Preto</span><span><i class="tree-dot red-dot"></i>Vermelho</span>' : '<span><i class="tree-dot avl-dot"></i>Nó da AVL</span>';
    $("tree-extremes").innerHTML = `Menor prontuário: ${tree.minimo ? escape(keyLabel(tree.minimo.prontuario)) : "—"}<span class="footer-divider"></span>Maior prontuário: ${tree.maximo ? escape(keyLabel(tree.maximo.prontuario)) : "—"}`;
    $("tree-empty").hidden = !!tree.raiz;
    $("tree-svg").hidden = !tree.raiz;
    if (tree.raiz) {
      const layout = graphLayout(tree.raiz);
      const viewport = $("tree-canvas").clientWidth - 18;
      const width = Math.max(viewport, layout.width);
      const offset = (width - layout.width) / 2;
      const path = searchPath(tree.raiz, app.highlighted);
      $("tree-svg").setAttribute("viewBox", `0 0 ${width} ${layout.height}`);
      $("tree-svg").setAttribute("width", width);
      $("tree-svg").setAttribute("height", layout.height);
      $("tree-svg").innerHTML = layout.edges.map(([parent, child]) => `<path class="tree-edge${path.has(parent.key) && path.has(child.key) ? " highlighted" : ""}" d="M${parent.x + offset} ${parent.y + 19} C${parent.x + offset} ${parent.y + 42},${child.x + offset} ${child.y - 42},${child.x + offset} ${child.y - 19}"/>`).join("") + layout.nodes.map((node) => {
        const red = ["vermelho", "V", "RED", "red"].includes(node.color);
        const colorClass = rn ? (red ? " red" : " black") : "";
        const keyText = escape(node.key);
        const fontSize = String(node.key).length > 5 ? Math.max(5, 50 / String(node.key).length) : 11;
        return `<g class="tree-node${colorClass}${app.highlighted === node.key ? " found" : ""}" transform="translate(${node.x + offset},${node.y})" role="button" tabindex="0" aria-label="Consultar prontuário ${keyText}${rn ? (red ? ", nó vermelho" : ", nó preto") : ""}" data-node-key="${keyText}"><title>Prontuário ${keyText}</title><circle r="21"/><text style="font-size:${fontSize}px">${keyText}</text></g>`;
      }).join("");
      app.rootX = layout.top.x + offset;
      const signature = `${app.tree}/${tree.quantidade}/${tree.raiz.chave}`;
      if (signature !== app.graphSignature) { app.graphSignature = signature; centerTree(); }
    }
    renderTraversal();
    const stats = tree.estatisticas;
    const fields = [["Rotações na inserção", stats.rotacoes_insercao], ["Rotações na remoção", stats.rotacoes_remocao], ["Recolorações na inserção", stats.recoloracoes_insercao], ["Recolorações na remoção", stats.recoloracoes_remocao]];
    $("balance-metrics").innerHTML = fields.map(([label, value]) => `<div><span>${label}</span><strong>${number(value)}</strong></div>`).join("");
  }

  function centerTree() {
    const canvas = $("tree-canvas");
    canvas.scrollLeft = Math.max(0, app.rootX - canvas.clientWidth / 2);
    canvas.scrollTop = 0;
  }

  function renderTraversal() {
    document.querySelectorAll("[data-traversal]").forEach((button) => {
      const active = button.dataset.traversal === app.traversal;
      button.classList.toggle("selected", active);
      button.setAttribute("aria-pressed", String(active));
    });
    const keys = app.estado.arvores[app.tree].percursos[app.traversal];
    $("traversal-values").innerHTML = keys.length ? keys.map((key) => `<button class="traversal-key" data-node-key="${key}" aria-label="Consultar prontuário ${key}">${escape(key)}</button>`).join("") : '<span class="muted">Nenhum nó para percorrer.</span>';
  }

  function renderMiniTree() {
    const root = app.estado.arvores.AVL.raiz;
    const nodes = [];
    const edges = [];
    function walk(node, depth, x, parent) {
      if (!node || depth > 2) return;
      const y = 20 + depth * 41;
      if (parent) edges.push(`<path d="M${parent.x} ${parent.y + 10} L${x} ${y - 10}" stroke="#b8d5cb" stroke-width="1.3"/>`);
      nodes.push(`<circle cx="${x}" cy="${y}" r="12" fill="${depth ? "#e3f0eb" : "#cfe5dd"}" stroke="#c2ddd1"/><text x="${x}" y="${y + 1}" dominant-baseline="central" text-anchor="middle" fill="#649486" font-size="${String(node.chave).length > 4 ? 5 : 8}" font-family="inherit">${escape(node.chave)}</text>`);
      walk(node.esquerda, depth + 1, x - 47 / (depth + 1), { x, y });
      walk(node.direita, depth + 1, x + 47 / (depth + 1), { x, y });
    }
    walk(root, 0, 100, null);
    $("mini-tree").innerHTML = root ? `<svg viewBox="0 0 200 125">${edges.join("")}${nodes.join("")}</svg>` : '<svg viewBox="0 0 200 125"><path d="M100 35v18H50v31m50-31h50v31" fill="none" stroke="#c1dbd0" stroke-width="1.5"/><circle cx="100" cy="30" r="15" fill="#d9ebe3"/><circle cx="50" cy="90" r="13" fill="#e0eee7"/><circle cx="150" cy="90" r="13" fill="#e0eee7"/><path d="M95 30h10m-60 60h10m90 0h10" stroke="#9fc3b2" stroke-width="1.5" stroke-linecap="round"/></svg>';
  }

  function renderLogs() {
    const logs = app.estado.logs;
    $("operation-log-content").textContent = logs.length ? logs.join("\n") : "As próximas inserções e remoções aparecerão aqui.";
    $("log-count").textContent = `${number(logs.length)} ${logs.length === 1 ? "linha" : "linhas"}`;
    const last = [...logs].reverse().find((line) => /^(Cadastro|Remoção|Demonstração|Geração|Busca de|Validação|Estatísticas|Comparação concluída)/.test(line));
    $("last-operation-text").textContent = last || (logs.length ? "As últimas operações estão disponíveis no registro detalhado das árvores." : "Inserções e remoções revelam as rotações e mudanças de cor das árvores.");
  }

  // ============= EXPERIMENTOS =================

  function renderComparison() {
    const result = app.comparison;
    if (!result) return;
    const rows = result.resultados;
    $("experiment-empty").hidden = true;
    $("experiment-output").hidden = false;
    $("download-csv").disabled = false;
    $("experiment-description").textContent = `${number(rows[0].quantidade_inicial)} registros · semente ${rows[0].seed} · ${rows.length} medições${rows.every((row) => row.valido) ? " válidas" : ""}`;
    const groups = [...new Set(rows.map((row) => row.experimento))];
    const maximum = Math.max(...rows.map((row) => row.tempo_segundos * 1000), .0001);
    $("experiment-chart").innerHTML = groups.map((scenario) => {
      const values = rows.filter((row) => row.experimento === scenario);
      return `<div class="chart-group"><span>${escape(scenarios[scenario] || scenario)}</span>${values.map((row) => `<div class="chart-bar-row" aria-label="${escape(row.arvore)}, ${number(row.tempo_segundos * 1000, 4)} milissegundos"><i class="tree-dot ${row.arvore === "AVL" ? "avl-dot" : "rn-dot"}" aria-hidden="true"></i><div class="chart-track" aria-hidden="true"><div class="chart-bar${row.arvore === "AVL" ? "" : " rn"}" style="width:${row.tempo_segundos * 1000 / maximum * 100}%"></div></div><span>${number(row.tempo_segundos * 1000, 4)}</span></div>`).join("")}</div>`;
    }).join("");
    $("experiment-rows").innerHTML = rows.map((row) => `<tr><td>${escape(scenarios[row.experimento] || row.experimento)}</td><td><span class="key-badge">${escape(row.arvore)}</span></td><td>${number(row.altura_inicial)} → ${number(row.altura_final)}</td><td>${number(row.tempo_segundos * 1000, 4)}</td><td>${row.rotacoes === null ? "—" : number(row.rotacoes)}</td><td>${row.recoloracoes === null ? "—" : number(row.recoloracoes)}</td><td>${row.media_nos_visitados === null ? "—" : number(row.media_nos_visitados, 2)}</td></tr>`).join("");
  }

  function downloadCsv() {
    if (!app.comparison) return;
    const first = app.comparison.resultados[0];
    const blob = new Blob([app.comparison.csv_texto], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `comparativo_${first.quantidade_inicial}_seed${first.seed}_${new Date().toISOString().replace(/[:.]/g, "-")}.csv`;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast("CSV preparado para download.");
  }

  // ============= EVENTOS E FORMULÁRIOS =================

  document.addEventListener("click", (event) => {
    const navigation = event.target.closest("[data-view]");
    if (navigation) { showView(navigation.dataset.view); return; }
    const closing = event.target.closest("[data-close-dialog]");
    if (closing) { closing.closest("dialog").close(); return; }
    if (event.target.closest("[data-open-patient]")) { openPatientForm(); return; }
    const tree = event.target.closest("[data-tree]");
    if (tree) { setTree(tree.dataset.tree); return; }
    const traversal = event.target.closest("[data-traversal]");
    if (traversal) { app.traversal = traversal.dataset.traversal; renderTraversal(); return; }
    const detail = event.target.closest("[data-patient-detail]");
    if (detail) { searchPatient(Number(detail.dataset.patientDetail), detail); return; }
    const deletion = event.target.closest("[data-patient-delete]");
    if (deletion) { openDelete(Number(deletion.dataset.patientDelete)); return; }
    const node = event.target.closest("[data-node-key]");
    if (node) searchPatient(Number(node.dataset.nodeKey), node.tagName.toLowerCase() === "button" ? node : undefined);
  });
  $("tree-svg").addEventListener("keydown", (event) => {
    if (["Enter", " "].includes(event.key) && event.target.closest("[data-node-key]")) { event.preventDefault(); event.target.closest("[data-node-key]").dispatchEvent(new MouseEvent("click", { bubbles: true })); }
  });
  $("new-button").addEventListener("click", openPatientForm);
  document.querySelector(".skip-link").addEventListener("click", (event) => { event.preventDefault(); $("conteudo").focus(); $("conteudo").scrollIntoView({ block: "start" }); });
  $("help-button").addEventListener("click", () => $("help-dialog").showModal());
  $("patient-tree-select").addEventListener("change", (event) => setTree(event.target.value));
  $("patient-search").addEventListener("input", (event) => { app.search = event.target.value; app.page = 1; if (app.estado) renderPatients(); });
  $("clear-search-button").addEventListener("click", () => { app.search = ""; $("patient-search").value = ""; app.page = 1; renderPatients(); $("patient-search").focus(); });
  $("search-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const text = $("patient-search").value.trim().replace(/^#/, "");
    if (/^\d+$/.test(text)) searchPatient(Number(text), $("search-form").querySelector("button"));
    else if (!text) $("patient-search").focus();
    else toast("A lista foi filtrada pelo nome. Para consultar a árvore, informe um prontuário.");
  });
  $("previous-page").addEventListener("click", () => { app.page--; renderPatients(); });
  $("next-page").addEventListener("click", () => { app.page++; renderPatients(); });
  $("patient-form").addEventListener("submit", (event) => {
    event.preventDefault();
    perform($("save-patient-button"), async () => {
      const key = Number($("patient-key").value);
      if (!Number.isSafeInteger(key) || key <= 0) throw new Error("Informe um prontuário inteiro positivo válido.");
      const response = await api("/api/pacientes", { prontuario: key, nome: $("patient-name").value.trim(), data_nascimento: $("patient-birth").value, telefone: $("patient-phone").value.trim() });
      $("patient-dialog").close();
      app.highlighted = key;
      app.search = "";
      $("patient-search").value = "";
      const index = app.estado.pacientes.findIndex((p) => p.prontuario === key);
      app.page = Math.floor(index / PAGE_SIZE) + 1;
      renderPatients();
      if (app.view === "arvores") renderTree();
      toast(response.mensagem);
    }, "patient-form-error");
  });
  $("demo-button").addEventListener("click", () => perform($("demo-button"), async () => {
    const response = await api("/api/demonstracao", {});
    toast(response.mensagem);
  }));
  $("generate-button").addEventListener("click", () => {
    const remaining = Math.max(0, 500 - (app.estado?.pacientes.length ?? 0));
    if (!remaining) { toast("A sessão já possui o limite de 500 pacientes.", true); return; }
    $("generate-count").max = remaining;
    $("generate-count").value = Math.min(20, remaining);
    $("generate-capacity").textContent = `Espaço para mais ${number(remaining)} pacientes nesta sessão.`;
    $("generate-form-error").hidden = true;
    $("generate-dialog").showModal();
  });
  $("generate-form").addEventListener("submit", (event) => {
    event.preventDefault();
    perform($("generate-submit"), async () => {
      const response = await api("/api/gerar", { quantidade: Number($("generate-count").value), seed: Number($("generate-seed").value) });
      $("generate-dialog").close();
      app.search = "";
      $("patient-search").value = "";
      renderPatients();
      toast(response.mensagem);
    }, "generate-form-error");
  });
  $("confirm-delete").addEventListener("click", () => perform($("confirm-delete"), async () => {
    const response = await api("/api/remover", { prontuario: app.deleting });
    if (app.highlighted === app.deleting) app.highlighted = null;
    $("delete-dialog").close();
    toast(response.mensagem);
  }, "delete-error"));
  $("detail-tree-button").addEventListener("click", () => {
    $("detail-dialog").close();
    app.highlighted = app.detail?.prontuario ?? null;
    showView("arvores");
    $("tree-canvas").focus();
  });
  $("validate-button").addEventListener("click", () => perform($("validate-button"), async () => { const response = await api("/api/validar", {}); toast(response.mensagem, !Object.values(response.resultado).every(Boolean)); }));
  $("reset-metrics-button").addEventListener("click", () => perform($("reset-metrics-button"), async () => { const response = await api("/api/metricas/reset", {}); toast(response.mensagem); }));
  $("center-tree-button").addEventListener("click", centerTree);
  $("see-log-button").addEventListener("click", () => { showView("arvores"); $("operation-log").open = true; $("operation-log").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "start" }); });
  $("experiment-form").addEventListener("submit", (event) => {
    event.preventDefault();
    perform($("experiment-button"), async () => {
      const previous = $("experiment-button").innerHTML;
      $("experiment-button").innerHTML = `${icon("reset")}Executando medições…`;
      try {
        const response = await api("/api/experimentos", { tamanho: Number($("experiment-size").value), seed: Number($("experiment-seed").value) });
        app.comparison = response.resultado;
        renderComparison();
        toast(response.mensagem);
      } finally { $("experiment-button").innerHTML = previous; }
    });
  });
  $("download-csv").addEventListener("click", downloadCsv);
  $("retry-button").addEventListener("click", () => perform($("retry-button"), () => api("/api/estado")));
  window.addEventListener("hashchange", () => { const view = location.hash.slice(1); if (views[view]) showView(view, false); });
  let resizeTimer;
  window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { if (app.estado && app.view === "arvores") renderTree(); }, 150); });
  // Uma segunda aba pode ter alterado o cadastro; a leitura não altera métricas.
  window.addEventListener("focus", () => { if (!app.pending && !document.querySelector("dialog[open]")) api("/api/estado").catch(() => {}); });
  showView(location.hash.slice(1) || "pacientes", false);
  api("/api/estado").catch((error) => toast(error.message, true));
})();
