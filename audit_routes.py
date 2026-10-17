"""Minimal staff mutation metadata; never copy bodies, query strings or files."""
import json
import sqlite3
import time
from flask import request

# Explicit endpoint coverage avoids accidentally retaining credentials or tokens
# when new account/provider routes are introduced.
CONTENT_ACTIONS = {
    'structured_bank_save', 'lao_draft_pack_import', 'rename_course_module',
    'site_settings_save', 'teacher_assignments_save', 'speaking_save', 'create_course', 'create_course_lesson', 'save_course_lesson',
    'lesson_access_save', 'course_order_save', 'course_level_save', 'course_metadata_save', 'course_sequence', 'course_premium', 'save_word', 'import_words',
    'upload_word_audio', 'bank_save', 'review_question', 'mock_config_save',
    'media_upload', 'media_publish', 'generate_audio', 'review_generated_audio',
    'moderate_post', 'plan_update', 'payment_review',
    'admin_create_lesson', 'admin_edit_lesson', 'admin_delete_lesson',
    'admin_reorder', 'admin_add_video', 'admin_toggle_video', 'admin_delete_video',
    'admin_add_question', 'admin_edit_question', 'admin_delete_question',
}


def install_audit(app, legacy, db):
    @app.after_request
    def record_staff_mutation(response):
        action = request.endpoint
        if action not in CONTENT_ACTIONS or request.method not in ('POST', 'PUT', 'PATCH', 'DELETE') or not 200 <= response.status_code < 300:
            return response
        user = legacy['current_user']()
        if not user or user.get('role') not in ('admin','superadmin','teacher'):
            return response
        # Import previews are read-only even though they use POST.
        result = response.get_json(silent=True) if response.is_json else None
        if action == 'import_words' and (not isinstance(result, dict) or not result.get('added')):
            return response
        target = dict(request.view_args or {})
        if isinstance(result, dict):
            if isinstance(result.get('id'), (str, int)):
                target['id'] = result['id']
            if action == 'admin_create_lesson' and isinstance(result.get('lesson'), dict):
                target['id'] = result['lesson'].get('id')
            if action == 'import_words':
                target['added'] = result['added']
        try:
            with db() as c:
                c.execute('INSERT INTO audit_log (actor,action,target,created) VALUES (?,?,?,?)',
                          (user['username'], action, json.dumps(target, ensure_ascii=False, sort_keys=True), time.time()))
        except sqlite3.Error:
            # The mutation is already committed. Do not falsely report it failed
            # and cause the client to repeat it. Operators must monitor this log.
            app.logger.error('Staff mutation audit write failed for endpoint %s', action)
        return response
