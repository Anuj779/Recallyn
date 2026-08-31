package com.recallyn.app.data.api

data class HealthResponse(val status: String)

data class WorkflowResponse(
    val id: String,
    val goal: String,
    val steps: Int,
    val version: String,
    val recipient: String?,
    val source: String?,
    val trigger: String?,
    val risk: String?,
    val tools: String?,
    val last_run: String?
)

data class TeachRequest(val prompt: String)
data class TeachResponse(val status: String, val workflow: Any)
data class ApproveRequest(val decision: String, val file_id: String? = null, val original_file_id: String? = null)

data class LogEntry(
    val type: String,
    val msg: String?,
    val tool: String?,
    val url: String?,
    val handoff_type: String?
)

data class PendingAction(
    val type: String,
    val message: String?,
    val tool: String?,
    val risk: String?,
    val reason: String?,
    val action_type: String? = null,
    val payload: Map<String, Any>? = null
)

data class RunStateResponse(
    val run_id: String,
    val workflow_id: String,
    val phase: String,
    val status: String,
    val step_idx: Int,
    val logs: List<LogEntry>?,
    val pending_action: PendingAction?
)


data class UploadResponse(val file_id: String, val filename: String, val source: String)


data class MobileActionResultRequest(
    val status: String,
    val action_type: String
)
