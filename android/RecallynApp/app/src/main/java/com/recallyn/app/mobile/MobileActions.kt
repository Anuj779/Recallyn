package com.recallyn.app.mobile

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.util.Log

object MobileActions {
    fun handleAction(context: Context, actionType: String, payload: Map<String, Any>?, onHandoff: (String) -> Unit) {
        try {
            when (actionType) {
                "OPEN_EMAIL_COMPOSE" -> {
                    val toList = payload?.get("to") as? List<*>
                    val to = toList?.firstOrNull()?.toString() ?: ""
                    val subject = payload?.get("subject")?.toString() ?: ""
                    val body = payload?.get("body")?.toString() ?: ""

                    val intent = Intent(Intent.ACTION_SENDTO).apply {
                        data = Uri.parse("mailto:")
                        putExtra(Intent.EXTRA_EMAIL, arrayOf(to))
                        putExtra(Intent.EXTRA_SUBJECT, subject)
                        putExtra(Intent.EXTRA_TEXT, body)
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    }

                    try {
                        context.startActivity(intent)
                        onHandoff("HANDOFF_COMPLETED")
                    } catch (e: android.content.ActivityNotFoundException) {
                        Log.e("MobileActions", "No compatible email app found.")
                        onHandoff("NO_COMPATIBLE_EMAIL_APP")
                    }

                }
                else -> {
                    Log.w("MobileActions", "Unknown action type: ")
                }
            }
        } catch (e: Exception) {
            Log.e("MobileActions", "Failed to launch action ", e)
            onHandoff("FAILED")
        }
    }
}
