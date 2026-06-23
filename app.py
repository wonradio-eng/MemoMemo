"""
TodoMaster — Streamlit 버전
PRD 기준 P0 기능 전체 구현:
  F-01 할일 추가 / F-02 수정 / F-03 삭제(Undo) / F-04 완료 체크
  F-05 카테고리 필터 / F-06 진행률 / F-07 데이터 영속성 (JSON 파일)
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

# ── 상수 ────────────────────────────────────────────────────────
DATA_FILE = Path("todomaster_data.json")

CAT_OPTIONS = {
    "전체":  "all",
    "🏢 업무":  "work",
    "🏠 개인": "personal",
    "📚 공부": "study",
}
CAT_LABEL = {
    "work":     "🏢 업무",
    "personal": "🏠 개인",
    "study":    "📚 공부",
}
CAT_COLOR = {
    "work":     "#2E86DE",
    "personal": "#27AE60",
    "study":    "#8E44AD",
}

# ── 데이터 레이어 (F-07) ────────────────────────────────────────
def load_todos() -> list[dict]:
    """JSON 파일에서 할일 목록을 읽는다. 파손 시 빈 목록으로 복구."""
    if not DATA_FILE.exists():
        return []
    try:
        raw = DATA_FILE.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            DATA_FILE.unlink(missing_ok=True)
            return []
        # 필수 필드 검증
        return [
            t for t in parsed
            if isinstance(t, dict)
            and isinstance(t.get("id"), str) and t["id"]
            and isinstance(t.get("text"), str) and t["text"].strip()
        ]
    except (json.JSONDecodeError, OSError):
        DATA_FILE.unlink(missing_ok=True)
        return []


def save_todos(todos: list[dict]) -> None:
    """할일 목록을 JSON 파일에 저장한다."""
    try:
        DATA_FILE.write_text(
            json.dumps(todos, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as e:
        st.error(f"저장 실패: {e}")


def now_iso() -> str:
    return datetime.now().isoformat()


# ── 세션 초기화 ─────────────────────────────────────────────────
def init_session():
    if "todos" not in st.session_state:
        st.session_state.todos = load_todos()
    if "filter_cat" not in st.session_state:
        st.session_state.filter_cat = "all"
    if "editing_id" not in st.session_state:
        st.session_state.editing_id = None   # 현재 편집 중인 항목 ID
    if "undo_todo" not in st.session_state:
        st.session_state.undo_todo = None    # 삭제 직전 항목 (Undo용)
    if "undo_index" not in st.session_state:
        st.session_state.undo_index = None


# ── CRUD 헬퍼 ───────────────────────────────────────────────────
def add_todo(text: str, category: str):
    text = text.strip()
    if not text:
        return
    todo = {
        "id":        str(uuid.uuid4()),
        "text":      text,
        "category":  category,
        "completed": False,
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }
    st.session_state.todos.append(todo)
    save_todos(st.session_state.todos)


def toggle_todo(todo_id: str):
    for t in st.session_state.todos:
        if t["id"] == todo_id:
            t["completed"] = not t["completed"]
            t["updatedAt"] = now_iso()
            break
    save_todos(st.session_state.todos)


def delete_todo(todo_id: str):
    todos = st.session_state.todos
    idx = next((i for i, t in enumerate(todos) if t["id"] == todo_id), None)
    if idx is None:
        return
    st.session_state.undo_todo  = todos[idx]
    st.session_state.undo_index = idx
    todos.pop(idx)
    st.session_state.todos = todos
    save_todos(todos)


def restore_todo():
    if st.session_state.undo_todo is None:
        return
    idx   = st.session_state.undo_index
    todos = st.session_state.todos
    insert_at = min(idx, len(todos))
    todos.insert(insert_at, st.session_state.undo_todo)
    st.session_state.todos     = todos
    st.session_state.undo_todo  = None
    st.session_state.undo_index = None
    save_todos(todos)


def update_todo(todo_id: str, new_text: str, new_category: str):
    new_text = new_text.strip()
    if not new_text:
        return
    for t in st.session_state.todos:
        if t["id"] == todo_id:
            t["text"]      = new_text
            t["category"]  = new_category
            t["updatedAt"] = now_iso()
            break
    st.session_state.editing_id = None
    save_todos(st.session_state.todos)


# ── 진행률 계산 (F-06) ─────────────────────────────────────────
def stats(todos: list[dict]) -> dict:
    total = len(todos)
    done  = sum(1 for t in todos if t["completed"])
    pct   = round(done / total * 100) if total else 0
    return {"total": total, "done": done, "pct": pct}


# ── CSS 주입 ────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    /* 전체 배경 */
    .stApp { background: #F3F4F6; }

    /* 헤더 */
    .tm-header {
        background: linear-gradient(135deg, #1A5FA8, #2E86DE);
        color: white;
        padding: 28px 32px 24px;
        border-radius: 14px;
        margin-bottom: 20px;
    }
    .tm-header h1 { margin: 0; font-size: 24px; font-weight: 800; }
    .tm-header p  { margin: 6px 0 0; font-size: 13px; opacity: 0.8; }

    /* 카드 */
    .tm-card {
        background: white;
        border-radius: 12px;
        padding: 20px 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 12px;
    }

    /* 할일 카드 */
    .todo-card {
        background: white;
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 8px;
        border-left: 4px solid #E5E7EB;
        transition: box-shadow 0.15s;
    }
    .todo-card:hover { box-shadow: 0 6px 20px rgba(0,0,0,0.12); }
    .todo-card.work     { border-left-color: #2E86DE; }
    .todo-card.personal { border-left-color: #27AE60; }
    .todo-card.study    { border-left-color: #8E44AD; }
    .todo-card.completed { background: #F9FAFB; }
    .todo-card.completed .todo-text { text-decoration: line-through; color: #9CA3AF; }

    .todo-text {
        font-size: 14px; font-weight: 500; color: #1F2937;
        word-break: break-word; overflow-wrap: break-word;
    }
    .cat-badge {
        display: inline-block;
        font-size: 11px; font-weight: 600;
        padding: 2px 8px; border-radius: 20px; margin-left: 6px;
    }
    .cat-work     { background: #EBF4FF; color: #2E86DE; }
    .cat-personal { background: #EAFAF1; color: #27AE60; }
    .cat-study    { background: #F5EEF8; color: #8E44AD; }

    /* 진행률 바 */
    .progress-wrap {
        background: #E5E7EB; border-radius: 4px;
        height: 8px; overflow: hidden; flex: 1;
    }
    .progress-fill {
        height: 100%; border-radius: 4px;
        transition: width 0.4s ease;
    }

    /* Undo 배너 */
    .undo-bar {
        background: #1F2937; color: white;
        padding: 12px 20px; border-radius: 10px;
        font-size: 14px; margin-bottom: 12px;
    }

    /* 버튼 여백 정리 */
    div[data-testid="stHorizontalBlock"] { gap: 4px !important; }

    /* 빈 상태 */
    .empty-state {
        text-align: center; padding: 48px 24px;
        color: #6B7280; font-size: 14px; line-height: 1.8;
    }
    .empty-icon { font-size: 48px; display: block; margin-bottom: 12px; }
    </style>
    """, unsafe_allow_html=True)


# ── 진행률 카드 렌더 (F-06) ────────────────────────────────────
def render_progress(todos: list[dict]):
    all_s  = stats(todos)
    work_s = stats([t for t in todos if t["category"] == "work"])
    pers_s = stats([t for t in todos if t["category"] == "personal"])
    stud_s = stats([t for t in todos if t["category"] == "study"])

    st.markdown(f"""
    <div class="tm-card">
      <div style="display:flex;align-items:baseline;gap:6px;margin-bottom:20px;">
        <span style="font-size:32px;font-weight:800;color:#2E86DE;line-height:1">{all_s['pct']}</span>
        <span style="font-size:15px;font-weight:600;color:#6B7280;">% 완료</span>
        <span style="margin-left:auto;font-size:13px;color:#6B7280;">완료 {all_s['done']} / 전체 {all_s['total']}</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:10px;">
        {_bar_row("🏢 업무", work_s, "#2E86DE")}
        {_bar_row("🏠 개인", pers_s, "#27AE60")}
        {_bar_row("📚 공부", stud_s, "#8E44AD")}
      </div>
    </div>
    """, unsafe_allow_html=True)


def _bar_row(label: str, s: dict, color: str) -> str:
    return f"""
    <div style="display:flex;align-items:center;gap:10px;">
      <span style="width:64px;font-size:12px;font-weight:600;color:#6B7280;flex-shrink:0">{label}</span>
      <div class="progress-wrap">
        <div class="progress-fill" style="width:{s['pct']}%;background:{color}"></div>
      </div>
      <span style="width:36px;font-size:12px;color:#6B7280;text-align:right;flex-shrink:0">{s['pct']}%</span>
    </div>
    """


# ── 할일 카드 렌더 ─────────────────────────────────────────────
def render_todo_card(todo: dict):
    todo_id   = todo["id"]
    completed = todo["completed"]
    cat       = todo["category"]
    is_editing = st.session_state.editing_id == todo_id

    card_cls = f"todo-card {cat}" + (" completed" if completed else "")
    badge_cls = f"cat-badge cat-{cat}"

    if is_editing:
        # ── 편집 모드 ───────────────────────────────────────
        with st.container():
            st.markdown(f'<div class="tm-card" style="border-left:4px solid {CAT_COLOR[cat]};padding:14px 16px;">', unsafe_allow_html=True)
            e_col1, e_col2 = st.columns([3, 1])
            with e_col1:
                new_text = st.text_input(
                    "수정",
                    value=todo["text"],
                    key=f"edit_text_{todo_id}",
                    label_visibility="collapsed",
                )
            with e_col2:
                cat_keys = list(CAT_LABEL.keys())       # ['work','personal','study']
                cat_vals = list(CAT_LABEL.values())     # ['🏢 업무',...]
                cur_idx  = cat_keys.index(cat)
                new_cat_label = st.selectbox(
                    "카테고리",
                    cat_vals,
                    index=cur_idx,
                    key=f"edit_cat_{todo_id}",
                    label_visibility="collapsed",
                )
                new_cat = cat_keys[cat_vals.index(new_cat_label)]

            b1, b2, _ = st.columns([1, 1, 4])
            with b1:
                if st.button("저장", key=f"save_{todo_id}", type="primary"):
                    update_todo(todo_id, new_text, new_cat)
                    st.rerun()
            with b2:
                if st.button("취소", key=f"cancel_{todo_id}"):
                    st.session_state.editing_id = None
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    else:
        # ── 보기 모드 ───────────────────────────────────────
        text_style = "text-decoration:line-through;color:#9CA3AF;" if completed else "color:#1F2937;"
        st.markdown(f"""
        <div class="{card_cls}">
          <span class="todo-text" style="{text_style}">{_escape(todo['text'])}</span>
          <span class="{badge_cls}">{CAT_LABEL[cat]}</span>
        </div>
        """, unsafe_allow_html=True)

        # 체크박스 + 편집 + 삭제 버튼을 카드 아래에 배치
        b_cols = st.columns([0.5, 0.5, 0.5, 5])
        with b_cols[0]:
            check_label = "✅" if completed else "⬜"
            if st.button(check_label, key=f"chk_{todo_id}", help="완료 토글"):
                toggle_todo(todo_id)
                st.rerun()
        with b_cols[1]:
            if st.button("✏", key=f"edit_{todo_id}", help="수정"):
                st.session_state.editing_id = todo_id
                st.rerun()
        with b_cols[2]:
            if st.button("🗑", key=f"del_{todo_id}", help="삭제"):
                delete_todo(todo_id)
                st.rerun()


def _escape(text: str) -> str:
    """XSS 방지: HTML 특수문자 이스케이프."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;"))


# ── 메인 ────────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="TodoMaster",
        page_icon="🗂️",
        layout="centered",
    )
    init_session()
    inject_css()

    # ── 헤더 ────────────────────────────────────────────────
    st.markdown("""
    <div class="tm-header">
      <h1>🗂️ TodoMaster</h1>
      <p>할일을 카테고리별로 관리하세요</p>
    </div>
    """, unsafe_allow_html=True)

    # ── 진행률 카드 (F-06) ───────────────────────────────────
    render_progress(st.session_state.todos)

    # ── Undo 배너 (F-03) ────────────────────────────────────
    if st.session_state.undo_todo:
        deleted_text = _escape(st.session_state.undo_todo["text"])
        undo_col1, undo_col2 = st.columns([5, 1])
        with undo_col1:
            st.markdown(
                f'<div class="undo-bar">🗑 <b>{deleted_text}</b> 삭제됨</div>',
                unsafe_allow_html=True,
            )
        with undo_col2:
            if st.button("↩ 되돌리기", key="undo_btn", type="primary"):
                restore_todo()
                st.rerun()

    # ── 할일 추가 폼 (F-01) ─────────────────────────────────
    with st.container():
        st.markdown('<div class="tm-card">', unsafe_allow_html=True)
        f_col1, f_col2, f_col3 = st.columns([4, 1.5, 1])
        with f_col1:
            new_text = st.text_input(
                "새 할일",
                placeholder="새 할일을 입력하세요...",
                label_visibility="collapsed",
                key="new_todo_text",
            )
        with f_col2:
            new_cat_label = st.selectbox(
                "카테고리",
                list(CAT_LABEL.values()),
                label_visibility="collapsed",
                key="new_todo_cat",
            )
        with f_col3:
            add_clicked = st.button("➕ 추가", type="primary", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if add_clicked and new_text.strip():
        cat_keys = list(CAT_LABEL.keys())
        cat_vals = list(CAT_LABEL.values())
        new_cat  = cat_keys[cat_vals.index(new_cat_label)]
        add_todo(new_text.strip(), new_cat)
        st.rerun()

    # ── 카테고리 필터 탭 (F-05) ─────────────────────────────
    tab_labels = list(CAT_OPTIONS.keys())   # ["전체", "🏢 업무", ...]
    tab_values = list(CAT_OPTIONS.values()) # ["all", "work", ...]

    cur_tab_idx = tab_values.index(st.session_state.filter_cat)
    selected_tab = st.radio(
        "카테고리 필터",
        tab_labels,
        index=cur_tab_idx,
        horizontal=True,
        label_visibility="collapsed",
        key="filter_radio",
    )
    st.session_state.filter_cat = CAT_OPTIONS[selected_tab]

    # ── 할일 목록 렌더 ───────────────────────────────────────
    todos = st.session_state.todos
    cat_f = st.session_state.filter_cat

    filtered = todos if cat_f == "all" else [t for t in todos if t["category"] == cat_f]

    # 미완료 → 완료 순 정렬 (F-04)
    sorted_todos = [t for t in filtered if not t["completed"]] + \
                   [t for t in filtered if t["completed"]]

    # 탭 뱃지 표시용 미완료 카운트
    counts = {v: sum(1 for t in todos if (v == "all" or t["category"] == v) and not t["completed"])
              for v in tab_values}

    # 탭 바로 아래에 미완료 카운트 요약 표시
    badge_parts = []
    for label, val in CAT_OPTIONS.items():
        if val == "all":
            continue
        n = counts[val]
        if n:
            badge_parts.append(f"{label} **{n}**")
    if badge_parts:
        st.caption("미완료: " + "  ·  ".join(badge_parts))

    st.divider()

    if not sorted_todos:
        label = "전체" if cat_f == "all" else CAT_LABEL.get(cat_f, cat_f)
        msg   = "아직 할일이 없어요 🎉 새 할일을 추가해보세요!" if cat_f == "all" \
                else f"{label}에 할일이 없어요"
        st.markdown(f"""
        <div class="empty-state">
          <span class="empty-icon">😴</span>{msg}
        </div>
        """, unsafe_allow_html=True)
    else:
        for todo in sorted_todos:
            render_todo_card(todo)


if __name__ == "__main__":
    main()
