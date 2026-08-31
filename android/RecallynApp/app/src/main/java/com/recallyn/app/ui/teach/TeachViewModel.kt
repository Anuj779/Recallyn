package com.recallyn.app.ui.teach

import android.content.Context
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.recallyn.app.data.api.ApiClient
import com.recallyn.app.data.api.TeachRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import okhttp3.MediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody
import java.io.File

class TeachViewModel : ViewModel() {
    private val _creationState = MutableStateFlow<String>("IDLE")
    val creationState: StateFlow<String> = _creationState

    fun createAgent(prompt: String) {
        _creationState.value = "LOADING"
        viewModelScope.launch {
            try {
                val res = ApiClient.apiService.teachWorkflow(TeachRequest(prompt))
                _creationState.value = if(res.status == "success") "SUCCESS" else "ERROR"
            } catch (e: Exception) {
                _creationState.value = "ERROR"
            }
        }
    }
    fun uploadFile(context: Context, uri: Uri, onResult: (String?, String?) -> Unit) {
        viewModelScope.launch {
            try {
                val contentResolver = context.contentResolver
                
                // Get real filename
                var filename = "upload_file"
                val cursor = contentResolver.query(uri, null, null, null, null)
                if (cursor != null && cursor.moveToFirst()) {
                    val nameIndex = cursor.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
                    if (nameIndex != -1) {
                        filename = cursor.getString(nameIndex)
                    }
                    cursor.close()
                }

                val inputStream = contentResolver.openInputStream(uri)
                val file = File(context.cacheDir, filename)
                file.outputStream().use { output ->
                    inputStream?.copyTo(output)
                }
                
                val mediaType = MediaType.parse(contentResolver.getType(uri) ?: "multipart/form-data")
                val requestFile = RequestBody.create(mediaType, file)
                val body = MultipartBody.Part.createFormData("file", filename, requestFile)
                val response = ApiClient.apiService.uploadFile(body)
                onResult(response.file_id, response.filename)
            } catch (e: Exception) {
                e.printStackTrace()
                onResult(null, null)
                }
        }
    }
}
