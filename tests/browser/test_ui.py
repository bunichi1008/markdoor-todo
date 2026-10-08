from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

pytestmark = pytest.mark.browser


def test_create_edit_complete_filter_and_reload(page):
    from playwright.sync_api import expect

    expect(page.get_by_text("タスクはまだありません")).to_be_visible()
    page.get_by_label("タイトル", exact=False).fill("面接の準備")
    page.get_by_label("説明", exact=False).fill("仕様を確認する")
    page.get_by_role("button", name="タスクを追加", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("追加しました")
    card = page.locator(".task-card")
    expect(card).to_have_count(1)
    expect(card).to_contain_text("仕様を確認する")
    expect(card.locator("time")).to_contain_text("JST")
    card.locator(".task-title").click()
    editor = card.get_by_role("form", name="タスクを編集")
    editor.get_by_label("タイトル").fill("面接の準備・完了")
    editor.get_by_label("説明").fill("")
    editor.get_by_role("button", name="変更を保存", exact=True).click()
    expect(card).to_contain_text("面接の準備・完了")
    page.get_by_role("checkbox", name="完了にする").check()
    expect(card).to_have_class("task-card is-completed")
    page.get_by_role("button", name="未完了", exact=True).click()
    expect(card).to_have_count(0)
    page.get_by_role("button", name="完了", exact=True).click()
    expect(card).to_have_count(1)
    page.reload()
    expect(page.locator(".task-card.is-completed")).to_have_count(1)


def test_html_is_displayed_as_text_and_failed_save_keeps_input(page):
    from playwright.sync_api import expect

    title = '<img src=x onerror="window.injected=true">'
    page.get_by_label("タイトル", exact=False).fill(title)
    page.get_by_label("説明", exact=False).fill("<script>window.injected=true</script>")
    page.route(
        "**/api/tasks",
        lambda route: route.abort() if route.request.method == "POST" else route.continue_(),
    )
    page.get_by_role("button", name="タスクを追加", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text("通信")
    expect(page.get_by_label("タイトル", exact=False)).to_have_value(title)
    expect(page.get_by_role("button", name="タスクを追加", exact=True)).to_be_enabled()
    page.unroute("**/api/tasks")
    page.get_by_role("button", name="タスクを追加", exact=True).click()
    expect(page.locator(".task-card")).to_contain_text(title)
    expect(page.locator(".task-card img, .task-card script")).to_have_count(0)
    assert page.evaluate("window.injected") is None


def test_delete_cancel_pagination_and_last_page_recovery(page, live_url):
    from playwright.sync_api import expect

    for number in range(51):
        assert page.request.post(f"{live_url}/api/tasks", data={"title": f"Task {number}"}).ok
    page.reload()
    expect(page.locator(".task-card")).to_have_count(50)
    page.get_by_role("button", name="次へ", exact=True).click()
    expect(page.locator(".task-card")).to_have_count(1)
    expect(page.locator("#page-info")).to_have_text("2 / 2 ページ")
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.get_by_role("button", name="削除", exact=True).click()
    expect(page.locator(".task-card")).to_have_count(1)
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="削除", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("削除しました")
    expect(page.locator(".task-card")).to_have_count(50)
    expect(page.locator("#page-info")).to_have_text("1 / 1 ページ")
    expect(page.get_by_role("button", name="次へ", exact=True)).to_be_disabled()
    page.reload()
    expect(page.locator(".task-card")).to_have_count(50)


def test_controls_disabled_during_save(page):
    from playwright.sync_api import expect

    pending = []
    page.route(
        "**/api/tasks",
        lambda route: pending.append(route)
        if route.request.method == "POST"
        else route.continue_(),
    )
    page.get_by_label("タイトル", exact=False).fill("一度だけ保存")
    page.get_by_role("button", name="タスクを追加", exact=True).click()
    expect(page.get_by_role("button", name="保存中…", exact=True)).to_be_disabled()
    expect(page.get_by_label("タイトル", exact=False)).to_be_disabled()
    assert len(pending) == 1
    pending[0].continue_()
    expect(page.get_by_role("button", name="タスクを追加", exact=True)).to_be_enabled()
    expect(page.locator(".task-card")).to_have_count(1)


def test_validation_failed_edit_and_failed_state_change_can_be_retried(page, live_url):
    from playwright.sync_api import expect

    task = page.request.post(f"{live_url}/api/tasks", data={"title": "元のタイトル"}).json()
    page.reload()
    page.get_by_role("button", name="編集", exact=True).click()
    editor = page.get_by_role("form", name="タスクを編集")
    editor.get_by_label("タイトル").fill("　 ")
    editor.get_by_role("button", name="変更を保存", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text("1〜200文字")
    expect(editor.get_by_label("タイトル")).to_have_value("　 ")
    editor.get_by_label("タイトル").fill("変更後")
    page.route("**/api/tasks/*", lambda route: route.abort())
    page.get_by_role("button", name="変更を保存", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text("通信")
    expect(editor.get_by_label("タイトル")).to_have_value("変更後")
    expect(page.get_by_role("button", name="変更を保存", exact=True)).to_be_enabled()
    assert page.request.get(f"{live_url}/api/tasks/{task['id']}").json()["title"] == "元のタイトル"
    page.unroute("**/api/tasks/*")
    page.get_by_role("button", name="変更を保存", exact=True).click()
    expect(page.locator(".task-card")).to_contain_text("変更後")
    page.route("**/api/tasks/*", lambda route: route.abort())
    page.get_by_role("checkbox", name="完了にする").click()
    expect(page.get_by_role("checkbox", name="完了にする")).not_to_be_checked()
    expect(page.get_by_role("checkbox", name="完了にする")).to_be_enabled()


def test_successful_write_then_failed_refresh_does_not_resubmit_form(page):
    from playwright.sync_api import expect

    page.get_by_label("タイトル").fill("保存済み")
    page.route("**/api/tasks?*", lambda route: route.abort())
    page.get_by_role("button", name="タスクを追加", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("追加しました")
    expect(page.get_by_role("alert")).to_contain_text("操作は完了しました")
    expect(page.get_by_label("タイトル")).to_have_value("")
    page.unroute("**/api/tasks?*")
    page.get_by_role("button", name="再読み込み", exact=True).click()
    expect(page.locator(".task-card")).to_have_count(1)


def test_japan_time_and_responsive_layout(page, live_url):
    from playwright.sync_api import expect

    first = page.request.post(
        f"{live_url}/api/tasks",
        data={
            "title": "APIの設計を確認する",
            "description": "入力検証とエラー応答をチェックする。",
        },
    ).json()
    page.request.post(
        f"{live_url}/api/tasks",
        data={
            "title": "気づいたことをREADMEにまとめる",
            "description": "次に触る人にも伝わるように。",
        },
    )
    page.request.post(
        f"{live_url}/api/tasks", data={"title": "今日のタスクを書き出す", "completed": True}
    )
    page.reload()
    expect(page.locator(".task-card")).to_have_count(3)
    expected = (
        datetime.fromisoformat(first["created_at"])
        .astimezone(timezone(timedelta(hours=9)))
        .strftime("%Y/%m/%d %H:%M JST")
    )
    expect(page.locator("time").last).to_have_text(expected)
    Path("test-results").mkdir(exist_ok=True)
    page.screenshot(path="test-results/desktop.png", full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path="test-results/mobile.png", full_page=True)
    page.locator(".task-title").last.click()
    expect(page.get_by_role("form", name="タスクを編集")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path="test-results/inline-mobile.png", full_page=True)
    page.set_viewport_size({"width": 1280, "height": 900})
    page.screenshot(path="test-results/inline-desktop.png", full_page=True)


def test_inline_edit_cancel_switch_and_navigation_preserve_drafts(page, live_url):
    from playwright.sync_api import expect

    for title in ("タスクA", "タスクB"):
        page.request.post(f"{live_url}/api/tasks", data={"title": title})
    page.reload()
    page.locator("#title").fill("追加フォームの下書き")
    page.get_by_role("button", name="タスクA", exact=True).click()
    editor = page.get_by_role("form", name="タスクを編集")
    editor.get_by_label("タイトル").fill("未保存の変更")
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.get_by_role("button", name="タスクB", exact=True).click()
    expect(editor.get_by_label("タイトル")).to_have_value("未保存の変更")
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.get_by_role("button", name="完了", exact=True).click()
    expect(editor.get_by_label("タイトル")).to_have_value("未保存の変更")
    page.get_by_role("button", name="再読み込み", exact=True).click()
    expect(editor.get_by_label("タイトル")).to_have_value("未保存の変更")
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="タスクB", exact=True).click()
    expect(editor.get_by_label("タイトル")).to_have_value("タスクB")
    editor.get_by_label("説明").fill("取り消す説明")
    editor.get_by_role("button", name="キャンセル", exact=True).click()
    expect(editor).to_have_count(0)
    button = page.get_by_role("button", name="タスクB", exact=True)
    button.focus()
    button.press("Enter")
    expect(editor.get_by_label("説明")).to_have_value("")
    editor.get_by_label("説明").press("Escape")
    expect(editor).to_have_count(0)
    expect(button).to_be_focused()
    expect(page.locator("#title")).to_have_value("追加フォームの下書き")
    result = page.request.get(f"{live_url}/api/tasks").json()
    assert {item["title"] for item in result["items"]} == {"タスクA", "タスクB"}


def test_inline_save_is_locked_during_request_and_keeps_failed_draft(page, live_url):
    from playwright.sync_api import expect

    task = page.request.post(
        f"{live_url}/api/tasks", data={"title": "編集対象", "description": "説明をクリック"}
    ).json()
    page.reload()
    page.get_by_text("説明をクリック", exact=True).click()
    editor = page.get_by_role("form", name="タスクを編集")
    title = '<img src=x onerror="window.injected=true">'
    editor.get_by_label("タイトル").fill(title)
    editor.get_by_label("説明").fill("説明の1行目\n2行目")
    pending = []
    page.route("**/api/tasks/*", lambda route: pending.append(route))
    editor.get_by_label("説明").press("Control+Enter")
    expect(editor.get_by_role("button", name="保存中…", exact=True)).to_be_disabled()
    expect(editor.get_by_role("button", name="キャンセル", exact=True)).to_be_disabled()
    expect(editor.get_by_label("タイトル")).to_be_disabled()
    assert len(pending) == 1
    pending[0].abort()
    expect(page.get_by_role("alert")).to_contain_text("通信")
    expect(editor.get_by_label("タイトル")).to_have_value(title)
    expect(editor.get_by_label("説明")).to_have_value("説明の1行目\n2行目")
    expect(editor.get_by_role("button", name="変更を保存", exact=True)).to_be_enabled()
    page.unroute("**/api/tasks/*")
    editor.get_by_label("説明").press("Control+Enter")
    expect(editor).to_have_count(0)
    expect(page.locator(".task-card")).to_contain_text(title)
    expect(page.locator(".task-card img")).to_have_count(0)
    assert page.evaluate("window.injected") is None
    result = page.request.get(f"{live_url}/api/tasks/{task['id']}").json()
    assert result["title"] == title
    assert result["description"] == "説明の1行目\n2行目"
    page.reload()
    expect(page.locator(".task-card")).to_contain_text(title)


def test_inline_save_success_is_visible_when_refresh_fails(page, live_url):
    from playwright.sync_api import expect

    task = page.request.post(f"{live_url}/api/tasks", data={"title": "変更前"}).json()
    page.reload()
    page.get_by_role("button", name="変更前", exact=True).click()
    editor = page.get_by_role("form", name="タスクを編集")
    editor.get_by_label("タイトル").fill("変更済み")
    page.route(
        "**/api/tasks?*",
        lambda route: route.abort() if route.request.method == "GET" else route.continue_(),
    )
    editor.get_by_role("button", name="変更を保存", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("更新しました")
    expect(page.get_by_role("alert")).to_contain_text("操作は完了しました")
    expect(editor).to_have_count(0)
    expect(page.locator(".task-card")).to_contain_text("変更済み")
    assert page.request.get(f"{live_url}/api/tasks/{task['id']}").json()["title"] == "変更済み"
    page.unroute("**/api/tasks?*")
    page.get_by_role("button", name="再読み込み", exact=True).click()
    expect(page.locator(".task-card")).to_have_count(1)
    expect(page.locator(".task-card")).to_contain_text("変更済み")
