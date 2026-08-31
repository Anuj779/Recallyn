package com.recallyn.app.ui.run

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.OpenInNew
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material.icons.outlined.AutoAwesome
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.recallyn.app.mobile.MobileActions
import com.recallyn.app.ui.teach.TeachViewModel
import kotlinx.coroutines.launch

@Composable
fun RunScreen(
    workflowId: String, 
    onBack: () -> Unit, 
    viewModel: RunViewModel = viewModel(),
    teachViewModel: TeachViewModel = viewModel()
) {
    val runState by viewModel.runState.collectAsState()
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    
    val fileLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) {
            teachViewModel.uploadFile(context, uri) { fileId, _ ->
                if (fileId != null) {
                    val logMsg = viewModel.runState.value?.logs?.lastOrNull()?.msg ?: ""
                    val originalFileId = if (logMsg.contains(": ")) logMsg.split(": ")[1].trim() else ""
                    viewModel.approve("REPLACE_FILE", fileId, originalFileId)
                    scope.launch {
                        kotlinx.coroutines.delay(500)
                        viewModel.step()
                    }
                }
            }
        }
    }

    LaunchedEffect(workflowId) { viewModel.startWorkflow(workflowId) }

    LaunchedEffect(runState) {
        val state = runState ?: return@LaunchedEffect
        if (state.status == "RUNNING" && state.phase == "EXECUTION") {
            kotlinx.coroutines.delay(1000)
            viewModel.step()
        } else if (state.status == "RUNNING" && state.phase == "VERIFICATION") {
            kotlinx.coroutines.delay(1000)
            viewModel.verify()
        }
    }

    Column(modifier = Modifier.fillMaxSize().background(Color(0xFFF9FAFB)).padding(24.dp)) {
        // Top Bar
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier.size(40.dp).clip(CircleShape).background(Color.White).clickable { onBack() },
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = Color.Black)
            }
            Box(
                modifier = Modifier.clip(RoundedCornerShape(50)).background(Color.White).padding(horizontal = 16.dp, vertical = 8.dp)
            ) {
                Text("Engine", fontSize = 14.sp, fontWeight = FontWeight.Medium, color = Color.Black)
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        if (runState == null) {
            Column(modifier = Modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                CircularProgressIndicator(color = Color.Black)
                Spacer(modifier = Modifier.height(16.dp))
                Text("Initializing Agent...", fontSize = 18.sp, fontWeight = FontWeight.Medium)
            }
        } else {
            val state = runState!!
            Text("Automating task:", fontSize = 32.sp, fontWeight = FontWeight.Bold, color = Color.Black, lineHeight = 36.sp)
            Text(workflowId, fontSize = 32.sp, fontWeight = FontWeight.Bold, color = Color.Gray, lineHeight = 36.sp)
            
            Spacer(modifier = Modifier.height(8.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                val statusColor = if(state.status == "FAILED") Color(0xFFEF4444) else if(state.status == "RUNNING") Color(0xFF3B82F6) else Color(0xFF10B981)
                Box(modifier = Modifier.size(8.dp).clip(CircleShape).background(statusColor))
                Spacer(modifier = Modifier.width(8.dp))
                Text("${state.phase} | ${state.status}", fontSize = 14.sp, fontWeight = FontWeight.Medium, color = Color.Gray)
            }
            
            Spacer(modifier = Modifier.height(24.dp))

            LazyColumn(modifier = Modifier.weight(1f)) {
                val logs = state.logs ?: emptyList()
                items(logs) { log ->
                    val bgColor = if (log.type == "handoff") Color(0xFFE0F2FE) else if (log.type == "error") Color(0xFFFEE2E2) else Color.White
                    Card(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp).shadow(2.dp, RoundedCornerShape(20.dp)),
                        shape = RoundedCornerShape(20.dp),
                        colors = CardDefaults.cardColors(containerColor = bgColor)
                    ) {
                        Column(modifier = Modifier.padding(20.dp)) {
                            if (log.type == "handoff") {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Box(modifier = Modifier.size(32.dp).clip(RoundedCornerShape(8.dp)).background(Color.White), contentAlignment = Alignment.Center) {
                                        Icon(Icons.Outlined.AutoAwesome, contentDescription = "Action", tint = Color(0xFF3B82F6))
                                    }
                                    Spacer(modifier = Modifier.width(12.dp))
                                    Text(log.tool ?: "Action Prepared", fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = Color.Black)
                                }
                                Spacer(modifier = Modifier.height(16.dp))
                                Button(
                                    onClick = { /* MobileActions.launchIntent(context, log.url ?: "") */ },
                                    colors = ButtonDefaults.buttonColors(containerColor = Color.Black),
                                    shape = RoundedCornerShape(50),
                                    modifier = Modifier.fillMaxWidth().height(48.dp)
                                ) {
                                    Text("Open ${log.handoff_type?.uppercase() ?: "APP"}")
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Icon(Icons.Default.OpenInNew, contentDescription = "Open", modifier = Modifier.size(16.dp))
                                }
                            } else {
                                Row(verticalAlignment = Alignment.Top) {
                                    val icon = if (log.type == "error") Icons.Default.Error else if (log.type == "success") Icons.Default.CheckCircle else Icons.Default.Info
                                    val iconColor = if (log.type == "error") Color.Red else if (log.type == "success") Color(0xFF10B981) else Color.Gray
                                    Icon(icon, contentDescription = null, tint = iconColor, modifier = Modifier.size(20.dp))
                                    Spacer(modifier = Modifier.width(12.dp))
                                    Text(log.msg ?: "", fontSize = 15.sp, color = Color.DarkGray)
                                }
                            }
                        }
                    }
                }
            }


            
            if (state.status == "WAITING_FOR_MOBILE_ACTION" && state.pending_action != null) {
                val action = state.pending_action
                val actionType = action.action_type ?: ""
                val payloadMap = action.payload as? Map<String, Any>
                
                Card(
                    modifier = Modifier.fillMaxWidth().padding(top = 12.dp).shadow(4.dp, RoundedCornerShape(24.dp)),
                    shape = RoundedCornerShape(24.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFEFF6FF))
                ) {
                    Column(modifier = Modifier.padding(24.dp)) {
                        Text("Mobile Action Ready", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = Color.Black)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(actionType, fontSize = 14.sp, color = Color.DarkGray)
                        Spacer(modifier = Modifier.height(16.dp))
                        
                        Button(
                            onClick = {
                                com.recallyn.app.mobile.MobileActions.handleAction(context, actionType, payloadMap) { resultStatus ->
                                    viewModel.submitMobileActionResult(resultStatus, actionType)
                                }
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF3B82F6)),
                            shape = RoundedCornerShape(50),
                            modifier = Modifier.fillMaxWidth().height(48.dp)
                        ) {
                            Text("Launch Action", fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                        }
                    }
                }
            }

            if (state.status == "WAITING_FOR_FILE_REPLACEMENT") {
                
                Card(
                    modifier = Modifier.fillMaxWidth().padding(top = 12.dp).shadow(4.dp, RoundedCornerShape(24.dp)),
                    shape = RoundedCornerShape(24.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFFEE2E2))
                ) {
                    Column(modifier = Modifier.padding(24.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(modifier = Modifier.size(32.dp).clip(CircleShape).background(Color(0xFFEF4444)), contentAlignment = Alignment.Center) {
                                Icon(Icons.Default.Warning, contentDescription = "Warning", tint = Color.White, modifier = Modifier.size(20.dp))
                            }
                            Spacer(modifier = Modifier.width(12.dp))
                            Text("REQUIRED FILE NOT FOUND", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = Color(0xFF991B1B))
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(state.logs?.lastOrNull()?.msg ?: "A required input file is missing from the server.", color = Color(0xFF7F1D1D), fontSize = 14.sp)
                        Spacer(modifier = Modifier.height(16.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Button(onClick = { fileLauncher.launch("*/*") }, modifier = Modifier.weight(1f), colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFDC2626))) {
                                Text("Select Replacement")
                            }
                        }
                    }
                }
            }

            if (state.status == "WAITING_FOR_APPROVAL"
 && state.pending_action != null) {
                val action = state.pending_action
                Card(
                    modifier = Modifier.fillMaxWidth().padding(top = 12.dp).shadow(4.dp, RoundedCornerShape(24.dp)),
                    shape = RoundedCornerShape(24.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFFFFBEB))
                ) {
                    Column(modifier = Modifier.padding(24.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(modifier = Modifier.size(32.dp).clip(CircleShape).background(Color(0xFFF59E0B)), contentAlignment = Alignment.Center) {
                                Icon(Icons.Default.Warning, contentDescription = "Warning", tint = Color.White, modifier = Modifier.size(20.dp))
                            }
                            Spacer(modifier = Modifier.width(12.dp))
                            Text("Authorization Required", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = Color.Black)
                        }
                        
                        Spacer(modifier = Modifier.height(16.dp))
                        
                        if (action.type == "RISK") {
                            Text(action.tool ?: "", fontWeight = FontWeight.SemiBold, color = Color.Black)
                            Text("Risk Level: ${action.risk}", color = Color(0xFFEF4444), fontWeight = FontWeight.Bold, fontSize = 14.sp)
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(action.reason ?: "", color = Color.DarkGray, fontSize = 14.sp)
                        } else {
                            Text(action.message ?: "", color = Color.DarkGray, fontSize = 15.sp)
                        }
                        
                        Spacer(modifier = Modifier.height(20.dp))
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            Button(
                                onClick = { viewModel.approve("CANCEL") },
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE5E7EB), contentColor = Color.Black),
                                shape = RoundedCornerShape(50),
                                modifier = Modifier.weight(1f).height(48.dp)
                            ) { Text("Block", fontWeight = FontWeight.SemiBold) }
                            
                            Button(
                                onClick = { viewModel.approve("APPROVE") },
                                colors = ButtonDefaults.buttonColors(containerColor = Color.Black),
                                shape = RoundedCornerShape(50),
                                modifier = Modifier.weight(1f).height(48.dp)
                            ) { Text("Approve", fontWeight = FontWeight.SemiBold) }
                        }
                    }
                }
            }
        }
    }
}
