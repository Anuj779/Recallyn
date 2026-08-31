package com.recallyn.app.data.api

import okhttp3.OkHttpClient
import okhttp3.Interceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*

interface RecallynApi {
    @GET("/health")
    suspend fun checkHealth(): HealthResponse

    @GET("/workflows")
    suspend fun getWorkflows(): List<WorkflowResponse>

    @POST("/workflows/teach")
    suspend fun teachWorkflow(@Body req: TeachRequest): TeachResponse

    @POST("/workflows/{id}/run")
    suspend fun startRun(@Path("id") workflowId: String): RunStateResponse

    @POST("/runs/{run_id}/step")
    suspend fun stepRun(@Path("run_id") runId: String): RunStateResponse

    @POST("/runs/{run_id}/approve")
    suspend fun approveRun(@Path("run_id") runId: String, @Body req: ApproveRequest): RunStateResponse


    @POST("/runs/{run_id}/verify")
    suspend fun verifyRun(@Path("run_id") runId: String): RunStateResponse

    @Multipart
    @POST("/files/upload")
    suspend fun uploadFile(@Part file: okhttp3.MultipartBody.Part): UploadResponse


    @POST("/runs/{run_id}/mobile-action-result")
    suspend fun submitMobileActionResult(
        @Path("run_id") runId: String,
        @Body request: MobileActionResultRequest
    ): RunStateResponse
}

object ApiClient {
    var BASE_URL = "https://large-doors-rhyme.loca.lt"

    private val client = OkHttpClient.Builder().addInterceptor { chain ->
        val request = chain.request().newBuilder()
            .addHeader("Bypass-Tunnel-Reminder", "true")
            .build()
        chain.proceed(request)
    }.build()

    val apiService: RecallynApi by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(RecallynApi::class.java)
    }
}
