"use strict";

const byId = (id) => document.getElementById(id);
const state = { offset: 0, limit: 50, total: 0, filter: "", items: [], editor: null, busy: false };
const form = byId("task-form");
const titleInput = byId("title");
const descriptionInput = byId("description");
const dateFormat = new Intl.DateTimeFormat("ja-JP", {
  timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit",
  hour: "2-digit", minute: "2-digit", hour12: false,
});

function message(id, text = "") {
  byId(id).textContent = text;
  byId(id).hidden = !text;
}

function syncControls() {
  document.querySelectorAll("button, input, textarea").forEach((el) => { el.disabled = state.busy; });
  byId("previous").disabled = state.busy || state.offset === 0;
  byId("next").disabled = state.busy || state.offset + state.limit >= state.total;
  byId("save").textContent = state.busy ? "保存中…" : "タスクを追加";
  const inlineSave = document.querySelector(".inline-save");
  if (inlineSave) inlineSave.textContent = state.busy ? "保存中…" : "変更を保存";
  if (state.editor) {
    const checkbox = document.querySelector(`[data-task-id="${state.editor.id}"] input[type="checkbox"]`);
    if (checkbox) checkbox.disabled = true;
  }
  byId("tasks").setAttribute("aria-busy", String(state.busy));
  document.querySelectorAll("[data-filter]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.filter === state.filter));
  });
}

async function api(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    let response;
    try {
      response = await fetch(path, { ...options, signal: controller.signal,
        headers: { "Content-Type": "application/json", ...options.headers } });
    } catch {
      throw new Error("通信に失敗しました。接続を確認して再試行してください。");
    }
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      if (response.status === 422) {
        const fields = (Array.isArray(body.detail) ? body.detail : []).map((item) => item.loc.at(-1));
        if (fields.includes("title")) throw new Error("タイトルは前後の空白を除いて1〜200文字で入力してください。");
        if (fields.includes("description")) throw new Error("説明は5,000文字以内で入力してください。");
        throw new Error("入力内容を確認してください。");
      }
      throw new Error(typeof body.detail === "string" ? body.detail : "処理に失敗しました。再試行してください。");
    }
    return response.status === 204 ? null : await response.json();
  } finally {
    clearTimeout(timeout);
  }
}

async function run(operation) {
  if (state.busy) return;
  state.busy = true;
  message("notice");
  message("error");
  syncControls();
  try {
    await operation();
  } catch (error) {
    const prefix = byId("notice").hidden ? "" : "操作は完了しましたが、一覧を更新できませんでした。再読み込みしてください。 ";
    message("error", prefix + error.message);
  } finally {
    state.busy = false;
    syncControls();
  }
}

function hasUnsavedChanges() {
  const draft = state.editor;
  return draft && (draft.title !== draft.originalTitle || draft.description !== draft.originalDescription);
}

function discardEditor() {
  if (hasUnsavedChanges() && !window.confirm("編集中の変更を破棄しますか？")) return false;
  state.editor = null;
  renderCards();
  return true;
}

function focusTask(taskId) {
  document.querySelector(`[data-task-id="${taskId}"] .task-title-button`)?.focus();
}

function cancelEdit(taskId) {
  if (state.busy) return;
  state.editor = null;
  renderCards();
  focusTask(taskId);
}

function editTask(task) {
  if (state.busy || state.editor?.id === task.id || !discardEditor()) return;
  state.editor = {
    id: task.id, title: task.title, description: task.description ?? "",
    originalTitle: task.title, originalDescription: task.description ?? "",
  };
  renderCards();
  byId(`edit-title-${task.id}`).focus();
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderEditor(task) {
  const draft = state.editor;
  const editor = element("form", "inline-editor");
  editor.setAttribute("aria-label", "タスクを編集");
  for (const [field, text, tag, hintText] of [
    ["title", "タイトル", "input", "前後の空白を除いて1〜200文字"],
    ["description", "説明", "textarea", "5,000文字まで。空欄で説明を削除"],
  ]) {
    const id = `edit-${field}-${task.id}`;
    const label = element("label", "", text);
    label.htmlFor = id;
    const input = element(tag);
    input.id = id;
    input.name = field;
    input.value = draft[field];
    input.required = field === "title";
    if (tag === "textarea") input.rows = 4;
    input.setAttribute("aria-describedby", `${id}-hint`);
    input.addEventListener("input", () => { draft[field] = input.value; });
    const hint = element("p", "hint", hintText);
    hint.id = `${id}-hint`;
    editor.append(label, input, hint);
  }
  const actions = element("div", "inline-actions");
  const save = element("button", "primary inline-save", "変更を保存");
  save.type = "submit";
  const cancel = element("button", "", "キャンセル");
  cancel.type = "button";
  cancel.addEventListener("click", () => cancelEdit(task.id));
  actions.append(save, cancel);
  editor.append(actions);
  editor.addEventListener("keydown", (event) => {
    if (event.isComposing || state.busy) return;
    if (event.key === "Escape") {
      event.preventDefault();
      cancelEdit(task.id);
    } else if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      editor.requestSubmit();
    }
  });
  editor.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (state.busy) return;
    await run(async () => {
      const saved = await api(`/api/tasks/${task.id}`, {
        method: "PATCH", body: JSON.stringify({ title: draft.title, description: draft.description || null }),
      });
      state.items = state.items.map((item) => item.id === task.id ? saved : item);
      state.editor = null;
      renderCards();
      message("notice", "タスクを更新しました。");
      await loadTasks();
    });
    if (!state.editor) focusTask(task.id);
  });
  return editor;
}

function renderTask(task) {
  const card = element("article", `task-card${task.completed ? " is-completed" : ""}`);
  card.dataset.taskId = task.id;
  card.addEventListener("click", (event) => {
    if (!event.target.closest("button, input, textarea, form")) editTask(task);
  });
  const checkbox = element("input");
  checkbox.type = "checkbox";
  checkbox.checked = task.completed;
  checkbox.setAttribute("aria-label", task.completed ? "未完了にする" : "完了にする");
  checkbox.addEventListener("change", () => {
    const completed = checkbox.checked;
    run(async () => {
      try {
        await api(`/api/tasks/${task.id}`, { method: "PATCH", body: JSON.stringify({ completed }) });
      } catch (error) {
        checkbox.checked = task.completed;
        throw error;
      }
      message("notice", "状態を変更しました。");
      await loadTasks();
    });
  });
  const content = element("div", "task-content");
  if (state.editor?.id === task.id) {
    content.append(renderEditor(task));
    card.append(checkbox, content);
    return card;
  }
  const heading = element("h3", "task-title");
  const title = element("button", "task-title-button", task.title);
  title.type = "button";
  title.title = "クリックして編集";
  title.addEventListener("click", () => editTask(task));
  heading.append(title);
  content.append(heading);
  if (task.description) content.append(element("p", "task-description", task.description));
  const meta = element("div", "task-meta");
  const time = element("time", "", `${dateFormat.format(new Date(task.created_at))} JST`);
  time.dateTime = task.created_at;
  meta.append(element("span", "badge", task.completed ? "完了" : "未完了"), time);
  content.append(meta);
  const actions = element("div", "task-actions");
  const edit = element("button", "", "編集");
  edit.type = "button";
  edit.addEventListener("click", () => editTask(task));
  const remove = element("button", "delete", "削除");
  remove.type = "button";
  remove.addEventListener("click", () => {
    if (state.busy || !window.confirm(`「${task.title}」を削除しますか？`)) return;
    run(async () => {
      await api(`/api/tasks/${task.id}`, { method: "DELETE" });
      message("notice", "タスクを削除しました。");
      await loadTasks();
    });
  });
  actions.append(edit, remove);
  card.append(checkbox, content, actions);
  return card;
}

function renderCards() {
  byId("tasks").replaceChildren(...state.items.map(renderTask));
  syncControls();
}

async function loadTasks() {
  const fetchPage = () => {
    const query = new URLSearchParams({ limit: state.limit, offset: state.offset });
    if (state.filter) query.set("completed", state.filter);
    return api(`/api/tasks?${query}`);
  };
  let result = await fetchPage();
  if (state.offset > 0 && state.offset >= result.total) {
    state.offset = Math.floor(Math.max(0, result.total - 1) / state.limit) * state.limit;
    result = await fetchPage();
  }
  state.total = result.total;
  state.items = result.items;
  renderCards();
  byId("empty").hidden = result.items.length !== 0;
  byId("empty").querySelector("h3").textContent = state.filter ? "この状態のタスクはありません" : "タスクはまだありません";
  byId("total").textContent = `${state.total}件`;
  byId("page-info").textContent = `${Math.floor(state.offset / state.limit) + 1} / ${Math.max(1, Math.ceil(state.total / state.limit))} ページ`;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (state.busy || !discardEditor()) return;
  run(async () => {
    const payload = { title: titleInput.value, description: descriptionInput.value || null };
    await api("/api/tasks", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    state.offset = 0;
    state.filter = "";
    message("notice", "タスクを追加しました。");
    await loadTasks();
  });
});
byId("refresh").addEventListener("click", () => run(loadTasks));

function navigate(filter, offset) {
  if (state.busy || !discardEditor()) return;
  run(async () => {
    const previous = { filter: state.filter, offset: state.offset };
    state.filter = filter;
    state.offset = offset;
    try { await loadTasks(); }
    catch (error) { Object.assign(state, previous); throw error; }
  });
}
document.querySelectorAll("[data-filter]").forEach((button) => {
  button.addEventListener("click", () => navigate(button.dataset.filter, 0));
});
byId("previous").addEventListener("click", () => navigate(state.filter, Math.max(0, state.offset - state.limit)));
byId("next").addEventListener("click", () => navigate(state.filter, state.offset + state.limit));
window.addEventListener("beforeunload", (event) => {
  if (hasUnsavedChanges()) {
    event.preventDefault();
    event.returnValue = "";
  }
});
run(loadTasks);
