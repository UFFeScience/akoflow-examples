expected <- data.frame(
  frequency=rep(c("monthly", "quarterly", "yearly"), each=2),
  model=rep(c("ets", "theta"), 3),
  published=c(1.526, 1.649, 1.592, 1.661, 3.395, 3.015),
  count=rep(c(366L, 427L, 518L), each=2),
  horizon=rep(c(24L, 8L, 4L), each=2)
)

rows <- lapply(seq_len(nrow(expected)), function(i) {
  target <- expected[i, ]
  stem <- paste(target$frequency, target$model, sep="-")
  scores <- read.csv(paste0(stem, "-scores.csv"))
  predictions <- read.csv(paste0(stem, "-forecasts.csv"))
  stopifnot(nrow(scores) == target$count, !anyDuplicated(scores$series),
            nrow(predictions) == target$count * target$horizon,
            !anyDuplicated(predictions[c("series", "lead")]),
            setequal(predictions$series, scores$series),
            all(predictions$lead %in% seq_len(target$horizon)),
            all(is.finite(predictions$forecast)), all(is.finite(predictions$actual)))
  eligible <- is.finite(scores$mase)
  actual <- mean(scores$mase[eligible])
  stopifnot(is.finite(actual), abs(actual - target$published) <= 0.005)
  transform(target, observed=actual, eligible=sum(eligible), excluded=sum(!eligible))
})
results <- do.call(rbind, rows)
write.csv(results, "tourism-mase.csv", row.names=FALSE)

draw <- function(count, path) {
  png(path, width=1000, height=540, res=110)
  on.exit(dev.off())
  values <- matrix(results$observed, nrow=2)
  values[, seq_len(3) > count] <- NA_real_
  barplot(values, beside=TRUE, names.arg=c("Monthly", "Quarterly", "Yearly"),
          col=c("#196b58", "#ad5834"), ylim=c(0, 3.8), ylab="Mean MASE (lower is better)",
          main="Monash Tourism forecast error by frequency")
  legend("topleft", c("ETS", "Theta"), fill=c("#196b58", "#ad5834"), bty="n")
}
frames <- sprintf("tourism-frame-%d.png", 1:3)
for (i in seq_along(frames)) draw(i, frames[[i]])
stopifnot(file.copy(frames[[3]], "tourism-mase.png", overwrite=TRUE))
stopifnot(system2("convert", c("-delay", "100", "-loop", "0", frames, "tourism-mase.gif")) == 0)
unlink(frames)
frame_info <- system2("identify", "tourism-mase.gif", stdout=TRUE)
stopifnot(length(frame_info) == 3, file.info("tourism-mase.png")$size > 0)
writeLines(c('{"passed":true,"comparisons":6,"animation_frames":3}'), "validation.json")
