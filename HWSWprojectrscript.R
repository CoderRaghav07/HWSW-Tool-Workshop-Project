library(randomForest)
library(RODBC)

cat("Starting risk prediction...\n")

con <- odbcDriverConnect(
  "Driver={ODBC Driver 18 for SQL Server};
   Server=raghav-traffic-server.database.windows.net;
   Database=trafficdb;
   Uid=Areebe07;
   Pwd=your_password;
   Encrypt=yes;
   TrustServerCertificate=yes;"
)

model <- readRDS("accident_model.rds")

traffic <- sqlQuery(con, "SELECT * FROM traffic")

if (nrow(traffic) == 0) {
  cat("No data\n")
  quit(save="no")
}

colnames(traffic)[colnames(traffic) == "vehicle_density"] <- "Vehicle_Count"
colnames(traffic)[colnames(traffic) == "avg_speed"] <- "Vehicle_Speed"

traffic$Vehicle_Count <- as.numeric(traffic$Vehicle_Count)
traffic$Vehicle_Speed <- as.numeric(traffic$Vehicle_Speed)

traffic$Congestion_Level <- traffic$Vehicle_Count / max(traffic$Vehicle_Count, na.rm = TRUE)

traffic <- na.omit(traffic)

traffic$Predicted_Traffic <- predict(model, newdata = traffic)

max_val <- max(traffic$Predicted_Traffic, na.rm = TRUE)

if (max_val == 0) {
  traffic$Accident_Risk <- 0
} else {
  traffic$Accident_Risk <- traffic$Predicted_Traffic / max_val
}

write.csv(traffic, "risk_output.csv", row.names = FALSE)

cat("✅ R completed\n")