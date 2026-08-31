package com.recallyn.app.ui.home

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.outlined.SmartToy
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.recallyn.app.data.api.ApiClient
import com.recallyn.app.data.api.WorkflowResponse

@Composable
fun HomeScreen(onNavigateToTeach: () -> Unit, onLaunchWorkflow: (String) -> Unit) {
    var workflows by remember { mutableStateOf<List<WorkflowResponse>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }

    LaunchedEffect(Unit) {
        try {
            workflows = ApiClient.apiService.getWorkflows()
        } catch (e: Exception) {
            e.printStackTrace()
        } finally {
            isLoading = false
        }
    }

    Column(modifier = Modifier.fillMaxSize().background(Color(0xFFF9FAFB)).padding(24.dp)) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Box(modifier = Modifier.size(40.dp).clip(CircleShape).background(Color.White), contentAlignment = Alignment.Center) {
                Icon(Icons.Default.Search, contentDescription = "Search", tint = Color.Black)
            }
            Box(
                modifier = Modifier.clip(RoundedCornerShape(50)).background(Color.Black).clickable { onNavigateToTeach() }.padding(horizontal = 16.dp, vertical = 10.dp)
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Add, contentDescription = "New", tint = Color.White, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("New Agent", fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = Color.White)
                }
            }
        }

        Spacer(modifier = Modifier.height(32.dp))
        Text("Your Workspace", fontSize = 36.sp, fontWeight = FontWeight.Bold, color = Color.Black)
        Spacer(modifier = Modifier.height(16.dp))
        
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Box(modifier = Modifier.clip(RoundedCornerShape(50)).background(Color.Black).padding(horizontal = 16.dp, vertical = 6.dp)) {
                Text("All ", color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.Medium)
            }
            Box(modifier = Modifier.clip(RoundedCornerShape(50)).background(Color(0xFFE5E7EB)).padding(horizontal = 16.dp, vertical = 6.dp)) {
                Text("Popular", color = Color.DarkGray, fontSize = 13.sp, fontWeight = FontWeight.Medium)
            }
        }
        Spacer(modifier = Modifier.height(24.dp))

        if (isLoading) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = Color.Black)
            }
        } else if (workflows.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("No workflows found. Create one!", color = Color.Gray)
            }
        } else {
            LazyColumn(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                items(workflows) { wf ->
                    val bgColor = when(wf.id.length % 3) {
                        0 -> Color(0xFFE0F2FE)
                        1 -> Color(0xFFFEF3C7)
                        else -> Color(0xFFF3E8FF)
                    }
                    
                    Card(
                        modifier = Modifier.fillMaxWidth().shadow(4.dp, RoundedCornerShape(24.dp)),
                        shape = RoundedCornerShape(24.dp),
                        colors = CardDefaults.cardColors(containerColor = bgColor)
                    ) {
                        Column(modifier = Modifier.padding(24.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Box(modifier = Modifier.size(40.dp).clip(CircleShape).background(Color.White), contentAlignment = Alignment.Center) {
                                    Icon(Icons.Outlined.SmartToy, contentDescription = "Agent", tint = Color.Black)
                                }
                                Spacer(modifier = Modifier.width(12.dp))
                                Text(
                                    wf.id.replace("wf_", "").replace("_", " ").split(' ').joinToString(" ") { it.replaceFirstChar { c -> c.uppercase() } } + " Agent",
                                    fontSize = 18.sp, fontWeight = FontWeight.Bold, color = Color.Black
                                )
                            }
                            
                            Spacer(modifier = Modifier.height(12.dp))
                            Text(wf.goal, color = Color(0xFF4B5563), fontSize = 15.sp, lineHeight = 20.sp)
                            
                            Spacer(modifier = Modifier.height(16.dp))
                            
                            Column(modifier = Modifier.background(Color.White.copy(alpha = 0.5f), RoundedCornerShape(12.dp)).padding(12.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(Icons.Default.Folder, contentDescription = "Source", modifier = Modifier.size(14.dp), tint = Color.DarkGray)
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text(wf.source ?: "Unknown", fontSize = 13.sp, color = Color.DarkGray)
                                }
                                Spacer(modifier = Modifier.height(6.dp))
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(Icons.Default.AccountCircle, contentDescription = "Recipient", modifier = Modifier.size(14.dp), tint = Color.DarkGray)
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text(wf.recipient ?: "Unknown", fontSize = 13.sp, color = Color.DarkGray)
                                }
                                Spacer(modifier = Modifier.height(6.dp))
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(Icons.Default.Link, contentDescription = "Tools", modifier = Modifier.size(14.dp), tint = Color.DarkGray)
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text(wf.tools ?: "", fontSize = 13.sp, color = Color.DarkGray)
                                }
                            }
                            
                            Spacer(modifier = Modifier.height(16.dp))
                            
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                Column {
                                    Text("v •  steps", fontSize = 12.sp, color = Color.Gray, fontWeight = FontWeight.Bold)
                                    Text("Last Run: ", fontSize = 12.sp, color = Color(0xFF10B981))
                                }
                                
                                Box(
                                    modifier = Modifier.clip(RoundedCornerShape(50)).background(Color.Black).clickable { onLaunchWorkflow(wf.id) }.padding(horizontal = 16.dp, vertical = 8.dp)
                                ) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Text("RUN WORKFLOW", color = Color.White, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                                        Spacer(modifier = Modifier.width(4.dp))
                                        Icon(Icons.Default.PlayArrow, contentDescription = "Play", tint = Color.White, modifier = Modifier.size(14.dp))
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
