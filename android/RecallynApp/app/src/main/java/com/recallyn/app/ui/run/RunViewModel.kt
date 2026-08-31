package com.recallyn.app.ui.run

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.recallyn.app.data.api.ApiClient
import com.recallyn.app.data.api.ApproveRequest
import com.recallyn.app.data.api.RunStateResponse
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class RunViewModel : ViewModel() {
    private val _runState = MutableStateFlow<RunStateResponse?>(null)
    val runState: StateFlow<RunStateResponse?> = _runState

    fun startWorkflow(workflowId: String) {
        viewModelScope.launch {
            try {
                _runState.value = ApiClient.apiService.startRun(workflowId)
            } catch (e: Exception) { e.printStackTrace() }
        }
    }

    fun step() {
        val current = _runState.value ?: return
        viewModelScope.launch {
            try {
                _runState.value = ApiClient.apiService.stepRun(current.run_id)
            } catch (e: Exception) { e.printStackTrace() }
        }
    }

    fun verify() {
        val current = _runState.value ?: return
        viewModelScope.launch {
            try {
                _runState.value = ApiClient.apiService.verifyRun(current.run_id)
            } catch (e: Exception) { e.printStackTrace() }
        }
    }
    fun approve(decision: String, fileId: String? = null, originalFileId: String? = null) {
        val current = _runState.value ?: return
        viewModelScope.launch {
            try {
                _runState.value = ApiClient.apiService.approveRun(current.run_id, ApproveRequest(decision, fileId, originalFileId))
            } catch (e: Exception) { e.printStackTrace() }
        }
    }

    fun submitMobileActionResult(status: String, actionType: String) {
        val current = _runState.value ?: return
        viewModelScope.launch {
            try {
                val res = ApiClient.apiService.submitMobileActionResult(current.run_id, com.recallyn.app.data.api.MobileActionResultRequest(status, actionType))
                _runState.value = res
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }
}
