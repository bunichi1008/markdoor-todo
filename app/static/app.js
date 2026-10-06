"use strict";

const byId = (id) => document.getElementById(id);
const state = { offset: 0, limit: 50, total: 0, filter: "", editingId: null, busy: false };
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
  byId("save").textContent = state.busy ? "保存中…" : state.editingId === null ? "タスクを追加" : "変更を保存";
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

function resetForm() {
  state.editingId = null;
  form.reset();
  byId("form-heading").textContent = "新しいタスク";
  byId("cancel-edit").hidden = true;
}

function editTask(task) {
  if (state.busy) return;
  state.editingId = task.id;
  titleInput.value = task.title;
  descriptionInput.value = task.description ?? "";
  byId("form-heading").textContent = "タスクを編集";
  byId("cancel-edit").hidden = false;
  syncControls();
  titleInput.focus();
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderTask(task) {
  const card = element("article", `task-card${task.completed ? " is-completed" : ""}`);
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
  content.append(element("h3", "task-title", task.title));
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
      if (state.editingId === task.id) resetForm();
      message("notice", "タスクを削除しました。");
      await loadTasks();
    });
  });
  actions.append(edit, remove);
  card.append(checkbox, content, actions);
  return card;
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
  byId("tasks").replaceChildren(...result.items.map(renderTask));
  byId("empty").hidden = result.items.length !== 0;
  byId("empty").querySelector("h3").textContent = state.filter ? "この状態のタスクはありません" : "タスクはまだありません";
  byId("total").textContent = `${state.total}件`;
  byId("page-info").textContent = `${Math.floor(state.offset / state.limit) + 1} / ${Math.max(1, Math.ceil(state.total / state.limit))} ページ`;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  run(async () => {
    const editing = state.editingId !== null;
    const payload = { title: titleInput.value, description: descriptionInput.value || null };
    await api(editing ? `/api/tasks/${state.editingId}` : "/api/tasks", {
      method: editing ? "PATCH" : "POST", body: JSON.stringify(payload),
    });
    resetForm();
    if (!editing) { state.offset = 0; state.filter = ""; }
    message("notice", editing ? "タスクを更新しました。" : "タスクを追加しました。");
    await loadTasks();
  });
});
byId("cancel-edit").addEventListener("click", () => { resetForm(); syncControls(); });
byId("refresh").addEventListener("click", () => run(loadTasks));

function navigate(filter, offset) {
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
run(loadTasks);
