args <- commandArgs(trailingOnly = TRUE)
frequency <- args[[1]]
method <- args[[2]]
library(forecast)
season <- c(monthly = 12, quarterly = 4, yearly = 1)[[frequency]]
horizon <- c(monthly = 24, quarterly = 8, yearly = 4)[[frequency]]
path <- paste0("/app/data/", frequency, ".zip")
expected_md5 <- c(monthly="7b9a152b2736aff87bb5155f6a650693", quarterly="fc5fa2e1e08103c4b586d5a3bd5097fb", yearly="a0b9b63d7f855e76ac406ffbe9237267")
stopifnot(unname(tools::md5sum(path)) == expected_md5[[frequency]])
file <- unzip(path, list=TRUE)$Name[[1]]
connection <- unz(path, file)
lines <- readLines(connection, encoding="CP1252")
close(connection)
records <- lines[seq.int(match("@data", lines) + 1L, length(lines))]
records <- records[nzchar(records)]
rows <- lapply(strsplit(records, ":", fixed=TRUE), function(fields) {
  values <- as.numeric(strsplit(tail(fields, 1), ",", fixed=TRUE)[[1]])
  stopifnot(all(is.finite(values)), length(values) > horizon)
  list(id=fields[[1]], train=head(values, -horizon), test=tail(values, horizon))
})
fallbacks <- 0L
results <- lapply(rows, function(row) {
  y <- forecast::msts(row$train, seasonal.periods=season)
  prediction <- tryCatch(
    if (method == "ets") forecast::forecast(forecast::ets(y), h=horizon)$mean
    else forecast::thetaf(y, h=horizon)$mean,
    error=function(error) {
      fallbacks <<- fallbacks + 1L
      forecast::snaive(y, h=horizon)$mean
    })
  prediction[is.na(prediction)] <- 0
  stopifnot(length(prediction)==horizon)
  loss <- mean(abs(row$test - as.numeric(prediction)))
  score <- loss / mean(abs(diff(row$train, lag=season)))
  if (is.na(score)) score <- loss / mean(abs(diff(row$train)))
  list(id=row$id, score=score, prediction=as.numeric(prediction), actual=row$test)
})
scores <- vapply(results, function(result) result$score, numeric(1))
ids <- vapply(results, function(result) result$id, character(1))
stopifnot(!anyDuplicated(ids))
stem <- paste(frequency, method, sep="-")
write.csv(data.frame(series=ids, mase=scores), paste0(stem, "-scores.csv"), row.names=FALSE)
forecasts <- do.call(rbind, lapply(results, function(result) {
  data.frame(series=result$id, lead=seq_len(horizon), forecast=result$prediction, actual=result$actual)
}))
write.csv(forecasts, paste0(stem, "-forecasts.csv"), row.names=FALSE)
cat(sprintf("%s %s R=%s forecast=%s series=%d eligible=%d fallbacks=%d mean_mase=%.10f\n",
            frequency, method, getRversion(), packageVersion("forecast"), length(rows),
            sum(is.finite(scores)), fallbacks, mean(scores[is.finite(scores)])))
