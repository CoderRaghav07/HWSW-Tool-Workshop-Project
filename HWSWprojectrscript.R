# ============================================================
# HWSWprojectrscript.R
# Risk Prediction using Random Forest
# Reads from Supabase (live_traffic table)
# Writes predictions to Supabase (risk_output table)
# ============================================================

library(randomForest)
library(httr)
library(jsonlite)

cat("Starting risk prediction...\n")

# ============================================================
# SUPABASE CREDENTIALS
# ============================================================
SUPABASE_URL <- "https://nhlgbwbpwzdwdefwaurb.supabase.co"
SUPABASE_KEY <- "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5obGdid2Jwd3pkd2RlZndhdXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU5ODg4NzgsImV4cCI6MjA5MTU2NDg3OH0.FzqLky6xrsPtzmjJ0VFoFoljoY2C1AjRrixtkAG3iN8"

headers <- c(
  "apikey"        = SUPABASE_KEY,
  "Authorization" = paste("Bearer", SUPABASE_KEY),
  "Content-Type"  = "application/json"
)

# ============================================================
# STEP 1: READ live_traffic FROM SUPABASE
# ============================================================
cat("Reading live_traffic from Supabase...\n")

response <- GET(
  url     = paste0(SUPABASE_URL, "/rest/v1/live_traffic?select=*&order=time.desc&limit=500"),
  add_headers(.headers = headers)
)

if (status_code(response) != 200) {
  cat("ERROR reading from Supabase:", status_code(response), "\n")
  quit(save = "no")
}

traffic <- fromJSON(content(response, "text", encoding = "UTF-8"))

if (nrow(traffic) == 0) {
  cat("No data in live_traffic table\n")
  quit(save = "no")
}

cat(paste("Loaded", nrow(traffic), "rows from live_traffic\n"))

# ============================================================
# STEP 2: PREPARE DATA (same logic as your original script)
# ============================================================
colnames(traffic)[colnames(traffic) == "vehicle_density"] <- "Vehicle_Count"
colnames(traffic)[colnames(traffic) == "avg_speed"]       <- "Vehicle_Speed"

traffic$Vehicle_Count <- as.numeric(traffic$Vehicle_Count)
traffic$Vehicle_Speed <- as.numeric(traffic$Vehicle_Speed)

traffic$Congestion_Level <- traffic$Vehicle_Count / max(traffic$Vehicle_Count, na.rm = TRUE)

traffic <- na.omit(traffic)

# ============================================================
# STEP 3: LOAD MODEL AND PREDICT
# ============================================================
cat("Loading model and predicting...\n")

model <- readRDS("accident_model.rds")

traffic$Predicted_Traffic <- predict(model, newdata = traffic)

max_val <- max(traffic$Predicted_Traffic, na.rm = TRUE)
if (max_val == 0) {
  traffic$Accident_Risk <- 0
} else {
  traffic$Accident_Risk <- traffic$Predicted_Traffic / max_val
}

# Sensor risk (matches Wokwi LED logic)
traffic$sensor_risk <- ifelse(
  traffic$distance > 150, "LOW",
  ifelse(traffic$distance > 80, "MEDIUM", "HIGH")
)

cat(paste("Predictions complete for", nrow(traffic), "rows\n"))

# ============================================================
# STEP 4: WRITE PREDICTIONS TO risk_output IN SUPABASE
# ============================================================
cat("Writing predictions to Supabase risk_output...\n")

# Build payload matching risk_output table schema
payload <- data.frame(
  time              = as.character(traffic$time),
  location          = traffic$location,
  vehicle_count     = as.integer(traffic$Vehicle_Count),
  vehicle_speed     = as.integer(traffic$Vehicle_Speed),
  weather_code      = as.integer(traffic$weather_code),
  distance          = as.numeric(traffic$distance),
  sensor_risk       = traffic$sensor_risk,
  risk_level        = traffic$risk_level,
  date              = as.character(traffic$date),
  hour              = as.integer(traffic$hour),
  congestion_level  = round(traffic$Congestion_Level, 6),
  predicted_traffic = round(traffic$Predicted_Traffic, 4),
  accident_risk     = round(traffic$Accident_Risk, 6),
  stringsAsFactors  = FALSE
)

# Upload in batches of 50
batch_size <- 50
total_rows <- nrow(payload)

for (i in seq(1, total_rows, by = batch_size)) {
  batch <- payload[i:min(i + batch_size - 1, total_rows), ]
  batch_json <- toJSON(batch, auto_unbox = TRUE, na = "null")
  
  res <- POST(
    url     = paste0(SUPABASE_URL, "/rest/v1/risk_output"),
    add_headers(.headers = c(headers, "Prefer" = "return=minimal")),
    body    = batch_json,
    encode  = "raw"
  )
  
  if (status_code(res) %in% c(200, 201)) {
    cat(paste("  Uploaded rows", i, "to", min(i + batch_size - 1, total_rows), "\n"))
  } else {
    cat(paste("  ERROR on batch", i, ":", status_code(res), "\n"))
    cat(content(res, "text"), "\n")
  }
}

# Also save locally as backup CSV
write.csv(traffic, "risk_output.csv", row.names = FALSE)

cat("R script completed successfully!\n")
cat(paste("Total rows processed:", total_rows, "\n"))