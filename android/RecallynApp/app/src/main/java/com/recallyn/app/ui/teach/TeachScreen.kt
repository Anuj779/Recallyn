package com.recallyn.app.ui.teach

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.delay

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TeachScreen(onBack: () -> Unit, onAgentCreated: () -> Unit, viewModel: TeachViewModel = viewModel()) {
    var prompt by remember { mutableStateOf("") }
    val state by viewModel.creationState.collectAsState()

    LaunchedEffect(state) {
        if (state == "SUCCESS") {
            delay(1000)
            onAgentCreated()
        }
    }

    Column(modifier = Modifier.fillMaxSize().background(Color(0xFFF9FAFB)).padding(24.dp)) {
        Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier.size(40.dp).clip(CircleShape).background(Color.White).clickable { onBack() },
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = Color.Black)
            }
            Spacer(modifier = Modifier.width(16.dp))
            Text("Create Agent", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = Color.Black)
        }

        Spacer(modifier = Modifier.height(32.dp))

        Text("What should the agent do?", fontSize = 28.sp, fontWeight = FontWeight.Bold, color = Color.Black, lineHeight = 34.sp)
        Spacer(modifier = Modifier.height(8.dp))
        Text("Describe the workflow in plain English. The AI engine will instantly compile it into a secure, executable toolchain.", color = Color.Gray, fontSize = 15.sp)

        Spacer(modifier = Modifier.height(24.dp))

        OutlinedTextField(
            value = prompt,
            onValueChange = { prompt = it },
            modifier = Modifier.fillMaxWidth().height(200.dp),
            placeholder = { Text("e.g. Read the weekly report and email my manager a summary...") },
            colors = TextFieldDefaults.outlinedTextFieldColors(
                containerColor = Color.White,
                focusedBorderColor = Color.Black,
                unfocusedBorderColor = Color.LightGray
            ),
            shape = RoundedCornerShape(16.dp)
        )

        Spacer(modifier = Modifier.weight(1f))

        if (state == "LOADING") {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                CircularProgressIndicator(color = Color.Black)
            }
        } else if (state == "SUCCESS") {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                Text("Agent Created Successfully!", color = Color(0xFF10B981), fontWeight = FontWeight.Bold)
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        Button(
            onClick = { viewModel.createAgent(prompt) },
            enabled = prompt.isNotBlank() && state == "IDLE",
            colors = ButtonDefaults.buttonColors(containerColor = Color.Black, disabledContainerColor = Color.LightGray),
            modifier = Modifier.fillMaxWidth().height(56.dp),
            shape = RoundedCornerShape(50)
        ) {
            Icon(Icons.Default.AutoAwesome, contentDescription = "AI", tint = Color.White)
            Spacer(modifier = Modifier.width(8.dp))
            Text("Synthesize Workflow", fontSize = 16.sp, fontWeight = FontWeight.Bold)
        }
    }
}
