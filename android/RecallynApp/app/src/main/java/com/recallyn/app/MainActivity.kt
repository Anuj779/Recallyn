package com.recallyn.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.lightColorScheme
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.recallyn.app.ui.home.HomeScreen
import com.recallyn.app.ui.run.RunScreen
import com.recallyn.app.ui.teach.TeachScreen

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(colorScheme = lightColorScheme(background = Color(0xFFF9FAFB))) {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    val navController = rememberNavController()
                    
                    NavHost(navController = navController, startDestination = "home") {
                        composable("home") {
                            HomeScreen(
                                onNavigateToTeach = { navController.navigate("teach") },
                                onLaunchWorkflow = { wfId -> navController.navigate("run/$wfId") }
                            )
                        }
                        composable("teach") {
                            TeachScreen(
                                onBack = { navController.popBackStack() },
                                onAgentCreated = { navController.popBackStack() }
                            )
                        }
                        composable("run/{workflowId}") { backStackEntry ->
                            val wfId = backStackEntry.arguments?.getString("workflowId") ?: ""
                            RunScreen(
                                workflowId = wfId,
                                onBack = { navController.popBackStack() }
                            )
                        }
                    }
                }
            }
        }
    }
}
