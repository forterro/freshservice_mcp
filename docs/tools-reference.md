# Tools Reference

Each tool uses a unified `action` parameter to select the operation. Pass the action as the first argument along with the relevant parameters.

**36 tools** total (34 scoped + 2 discovery), organized into 13 independently loadable scopes.

## Ticket Management (`tickets` scope)

**`manage_ticket`** — Actions: `list`, `get`, `create`, `update`, `delete`, `filter`, `get_fields`

| Action | Required Parameters | Optional Parameters |
| ------ | ------------------- | ------------------- |
| `list` | — | `page`, `per_page` |
| `get` | `ticket_id` | `include` |
| `create` | `subject`, `description`, `email`, `priority`, `status` | `source`, `type`, `group_id`, `agent_id`, `custom_fields` |
| `update` | `ticket_id` | any updatable field |
| `delete` | `ticket_id` | — |
| `filter` | `query` | `page`, `per_page` |

**`manage_ticket_conversation`** — Actions: `list`, `create_reply`, `create_note`

**`manage_service_catalog`** — Actions: `list`, `get`

## Change Management (`changes` scope)

**`manage_change`** — Actions: `list`, `get`, `create`, `update`, `delete`, `close`, `filter`, `move`, `get_fields`

| Action | Required Parameters | Optional Parameters |
| ------ | ------------------- | ------------------- |
| `create` | `requester_id`, `subject`, `description`, `priority`, `impact`, `status`, `risk`, `change_type` | `planning_fields`*, `assets`, `impacted_services`, `custom_fields`, `agent_id`, `group_id` |
| `update` | `change_id` | any updatable field including `planning_fields`, `impacted_services` |
| `close` | `change_id` | `body` (result explanation) |

> *`planning_fields` on create are handled transparently via a 2-step process (POST + PUT) to work around a Freshservice API limitation.
> **`impacted_services`** is distinct from `assets`: use `assets` for CI associations (`[{"display_id": N}]`) and `impacted_services` for business service impact declarations (`[{"id": N, "status": 1}]`). Service statuses: 1=Operational, 5=Under maintenance, 10=Degraded, 20=Partial outage, 30=Major outage.

**`manage_change_note`** — Actions: `list`, `get`, `create`, `update`, `delete`

**`manage_change_task`** — Actions: `list`, `get`, `create`, `update`, `delete`

**`manage_change_time_entry`** — Actions: `list`, `get`, `create`, `update`, `delete`

**`manage_change_approval`** — Actions: `list`, `get`, `approve`, `reject`

## Problem Management (`problems` scope)

**`manage_problem`** — Actions: `list`, `get`, `create`, `update`, `delete`, `filter`, `close`, `restore`, `get_fields`

| Action | Required Parameters | Optional Parameters |
| ------ | ------------------- | ------------------- |
| `create` | `requester_id`, `subject`, `description`, `priority`, `status`, `impact`, `due_by` | `agent_id`, `group_id`, `department_id`, `known_error`, `category`, `analysis_fields`, `assets`, `custom_fields` |
| `close` | `problem_id` | — |

Priority: 1=Low, 2=Medium, 3=High, 4=Urgent · Status: 1=Open, 2=Change Requested, 3=Closed · Impact: 1=Low, 2=Medium, 3=High

**`manage_problem_note`** — Actions: `list`, `get`, `create`, `update`, `delete`

**`manage_problem_task`** — Actions: `list`, `get`, `create`, `update`, `delete`

**`manage_problem_time_entry`** — Actions: `list`, `get`, `create`, `update`, `delete`

## Release Management (`releases` scope)

**`manage_release`** — Actions: `list`, `get`, `create`, `update`, `delete`, `filter`, `restore`, `get_fields`

| Action | Required Parameters | Optional Parameters |
| ------ | ------------------- | ------------------- |
| `create` | `subject`, `description`, `priority`, `status`, `release_type`, `planned_start_date`, `planned_end_date` | `planning_fields`*, `agent_id`, `group_id`, `department_id`, `assets`, `custom_fields` |

> *Like changes, `planning_fields` on create uses transparent 2-step handling.

Priority: 1=Low, 2=Medium, 3=High, 4=Urgent · Status: 1=Open, 2=On hold, 3=In Progress, 4=Incomplete, 5=Completed · Type: 1=Minor, 2=Standard, 3=Major, 4=Emergency

**`manage_release_note`** — Actions: `list`, `get`, `create`, `update`, `delete`

**`manage_release_task`** — Actions: `list`, `get`, `create`, `update`, `delete`

**`manage_release_time_entry`** — Actions: `list`, `get`, `create`, `update`, `delete`

## Asset / CMDB Management (`assets` scope)

**`manage_asset`** — Actions: `list`, `get`, `create`, `update`, `delete`, `delete_permanently`, `restore`, `search`, `filter`, `move`, `get_fields`

**`manage_asset_details`** — Actions: `get_components`, `get_requests`, `get_contracts`, `get_installed_software`, `get_assignment_history`, `list_types`, `get_type`

**`manage_asset_relationship`** — Actions: `list`, `list_all`, `get`, `create`, `delete`, `get_types`

## Status Page (`status_page` scope)

**`manage_status_page`** — Maintenance windows, incidents, service components, and subscribers.

All actions auto-discover `status_page_id` if omitted. Maintenance CRUD requires either `change_id` **or** `maintenance_window_id` as the source entity. Incident CRUD requires `ticket_id`.

> **Publishing maintenance on the Status Page — workflow:**
>
> 1. Check the Change: `manage_change` action=`get` → inspect `maintenance_window`
> 2. **If `maintenance_window` has an `id`** → use `change_id` directly in `create_maintenance`
> 3. **If `maintenance_window` is empty `{}`** → create a MW with `manage_maintenance_window` action=`create` passing `change_id` (auto-associates the MW with the Change), then use the returned `maintenance_window_id` in `create_maintenance`
> 4. Required fields for `create_maintenance`: `title`, `description`, `started_at`, `ended_at`, `impacted_services` (get component IDs via `list_components`)

**`manage_maintenance_window`** — CRUD for Maintenance Windows. Pass `change_id` on create to auto-associate.

| Action | Required Parameters |
| ------ | ------------------- |
| `list` | — |
| `get` | `maintenance_window_id` |
| `create` | `name`, `start_time`, `end_time` + optional `change_id` (auto-associates) |
| `update` | `maintenance_window_id` |
| `delete` | `maintenance_window_id` |

**`manage_status_page`** actions:

| Action | Required Parameters |
| ------ | ------------------- |
| **Pages** | |
| `list_pages` | — |
| **Service Components** | |
| `list_components` | — |
| `get_component` | `component_id` |
| **Maintenance** (from Change or MW) | |
| `list_maintenance` | — |
| `create_maintenance` | `change_id` or `maintenance_window_id`, `title`, `description`, `started_at`, `ended_at`, `impacted_services` |
| `get_maintenance` | `change_id` or `maintenance_window_id`, `maintenance_id` |
| `update_maintenance` | `change_id` or `maintenance_window_id`, `maintenance_id` |
| `delete_maintenance` | `change_id` or `maintenance_window_id`, `maintenance_id` |
| **Maintenance Updates** | |
| `list_maintenance_updates` | `change_id` or `maintenance_window_id`, `maintenance_id` |
| `create_maintenance_update` | `change_id` or `maintenance_window_id`, `maintenance_id`, `body` |
| `update_maintenance_update` | `change_id` or `maintenance_window_id`, `maintenance_id`, `update_id` |
| `delete_maintenance_update` | `change_id` or `maintenance_window_id`, `maintenance_id`, `update_id` |
| **Incidents** (from Ticket) | |
| `list_incidents` | — |
| `create_incident` | `ticket_id`, `title` |
| `get_incident` / `update_incident` / `delete_incident` | `ticket_id`, `incident_id` |
| **Incident Updates** | |
| `list_incident_updates` | `ticket_id`, `incident_id` |
| `create_incident_update` | `ticket_id`, `incident_id`, `body` |
| `update_incident_update` | `ticket_id`, `incident_id`, `update_id` |
| `delete_incident_update` | `ticket_id`, `incident_id`, `update_id` |
| **Statuses** | |
| `list_maintenance_statuses` / `list_incident_statuses` | — |
| **Subscribers** | |
| `list_subscribers` | — |
| `get_subscriber` | `subscriber_id` |
| `create_subscriber` | `email` |
| `update_subscriber` | `subscriber_id` |
| `delete_subscriber` | `subscriber_id` |

Key fields: `started_at` (ISO datetime), `ended_at`, `impacted_services` (`[{id, status}]`), `notifications` (`[{trigger, options}]`), `description`.

## Project Management (`projects` scope)

**`manage_project`** — Actions: `create`, `update`, `get`, `list`, `delete`, `archive`, `restore`, `get_fields`, `get_templates`, `add_members`, `get_memberships`, `create_association`, `get_associations`, `delete_association`, `get_versions`, `get_sprints`

| Action | Required Parameters | Optional Parameters |
| ------ | ------------------- | ------------------- |
| `list` | — | `filter` (`completed`, `incomplete`, `archived`, `open`, `in_progress`), `page`, `per_page` |
| `get` | `project_id` | — |
| `create` | `name`, `project_type` (0=Software, 1=Business) | `description`, `key`, `priority_id`, `manager_id`, `start_date`, `end_date`, `visibility`, `sprint_duration`, `project_template_id`, `custom_fields` |
| `update` | `project_id` | any updatable field |
| `delete` | `project_id` | — |
| `archive` / `restore` | `project_id` | — |
| `get_fields` | — | — |
| `get_templates` | — | — |
| `add_members` | `project_id`, `members` (`[{"email": "...", "role": 1}]`) | — |
| `get_memberships` | `project_id` | — |
| `create_association` | `project_id`, `module_name` (`tickets`/`problems`/`changes`/`assets`), `ids` | — |
| `get_associations` | `project_id`, `module_name` | — |
| `delete_association` | `project_id`, `module_name`, `association_id` | — |
| `get_versions` / `get_sprints` | `project_id` | — |

Priority: 1=Low, 2=Medium, 3=High, 4=Urgent · Status: 1=Yet to start, 2=In Progress, 3=Completed · Visibility: 0=Private, 1=Public

**`manage_project_task`** — Actions: `create`, `update`, `get`, `list`, `filter`, `delete`, `get_task_types`, `get_task_type_fields`, `get_task_statuses`, `get_task_priorities`, `create_note`, `list_notes`, `update_note`, `delete_note`, `create_association`, `get_associations`, `delete_association`

| Action | Required Parameters | Optional Parameters |
| ------ | ------------------- | ------------------- |
| `list` | `project_id` | `filter`, `page`, `per_page` |
| `get` | `project_id`, `task_id` | — |
| `create` | `project_id`, `title`, `type_id` | `description`, `status_id`, `priority_id`, `assignee_id`, `reporter_id`, `parent_id`, `planned_start_date`, `planned_end_date`, `planned_effort`, `story_points`, `sprint_id`, `version_id`, `custom_fields` |
| `update` | `project_id`, `task_id` | any updatable field |
| `delete` | `project_id`, `task_id` | — |
| `filter` | `project_id`, `query` | `page`, `per_page` |
| `get_task_types` | `project_id` | — |
| `get_task_type_fields` | `project_id`, `type_id` | — |
| `get_task_statuses` / `get_task_priorities` | `project_id` | — |
| `create_note` | `project_id`, `task_id`, `content` | — |
| `list_notes` | `project_id`, `task_id` | — |
| `update_note` | `project_id`, `task_id`, `note_id`, `content` | — |
| `delete_note` | `project_id`, `task_id`, `note_id` | — |
| `create_association` | `project_id`, `task_id`, `module_name`, `ids` | — |
| `get_associations` | `project_id`, `task_id`, `module_name` | — |
| `delete_association` | `project_id`, `task_id`, `module_name`, `association_id` | — |

> Use `get_task_types` to discover available type_ids before creating tasks. The task UPDATE endpoint uses a singular path (`/task/` instead of `/tasks/`) — this is handled automatically.

## Departments & Locations (`departments` scope)

**`manage_department`** — Actions: `list`, `get`, `create`, `update`, `delete`, `filter`, `get_fields`

**`manage_location`** — Actions: `list`, `get`, `create`, `update`, `delete`, `filter`

## Agents & Requesters (`agents` / `requesters` scopes)

**`get_me`** — Returns the identity of the currently authenticated user.

With OAuth2 tokens (gateway mode), decodes the JWT to extract the user's email and queries the Freshservice agents API. With API key auth (local dev), calls `GET /api/v2/agents/me` directly.

**`manage_agent`** — Actions: `list`, `get`, `create`, `update`, `delete`, `filter`

**`manage_agent_group`** — Actions: `list`, `get`, `create`, `update`, `delete`

**`manage_requester`** — Actions: `list`, `get`, `create`, `update`, `delete`, `filter`, `merge`, `convert_to_agent`

**`manage_requester_group`** — Actions: `list`, `get`, `create`, `update`, `delete`

## Solutions, Products, Misc (`solutions` / `products` / `misc` scopes)

**`manage_solution`** — Actions: `list_categories`, `get_category`, `create_category`, `update_category`, `delete_category`, `list_folders`, `get_folder`, `create_folder`, `update_folder`, `delete_folder`, `list_articles`, `get_article`, `create_article`, `update_article`, `delete_article`

**`manage_product`** — Actions: `list`, `get`, `create`, `update`, `delete`

**`manage_canned_response`** — Actions: `list_folders`, `get_folder`, `list_responses`, `get_response`

**`manage_workspace`** — Actions: `list`, `get`

## Discovery Tools (always loaded)

**`discover_form_fields`** — Discover custom field definitions for any entity type (tickets, changes, problems, releases, assets, etc.). Essential for understanding available `custom_fields` before creating or updating entities.

**`clear_field_cache`** — Clear the in-memory cache of field definitions. Useful after custom fields have been added or modified in Freshservice.

## Query Syntax for Filtering

When using `filter` actions, **the query string is automatically wrapped in double quotes** by the server. Pass the raw query:

```text
action: "filter", query: "status:3 AND priority:1"
```

**Common filter examples:**

- `"status:3"` — Changes awaiting approval
- `"priority:3 AND status:1"` — High priority open problems
- `"planned_start_date:>'2025-07-14'"` — Changes starting after a date
