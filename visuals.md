# Current Visuals Summary

## Image 1: Core Performance Analysis

### Audio File Length vs Performance

**Description:** This scatter plot reveals how different AMT models handle varying audio durations, with trend lines showing each model's performance degradation or stability over time. The negative correlation (-0.106) suggests that longer audio files present increased challenges for accurate transcription across all models.

**Benefit:** Identifies which models maintain consistent performance regardless of audio length, crucial for real-world applications where song durations vary significantly.

### Precision vs Recall

**Description:** This plot demonstrates the fundamental trade-off between precision (accuracy of detected notes) and recall (completeness of note detection) for each model. The diagonal reference line shows perfect balance, while deviations indicate model-specific biases toward conservative or aggressive note detection.

**Benefit:** Reveals architectural differences in how models prioritize accuracy versus completeness, helping users choose models based on their specific transcription needs.

### F-measure vs Overlap Ratio

**Description:** This analysis shows how well each model's F-measure correlates with note overlap accuracy, indicating whether high-performing models also excel at temporal precision. The positive correlation (0.216) suggests that better models tend to have more accurate note timing.

**Benefit:** Validates that overall performance metrics align with temporal accuracy, ensuring comprehensive model evaluation beyond simple note detection.

### F-measure Distribution by Model

**Description:** These box plots reveal the performance consistency and range for each model, showing median performance, quartiles, and outliers. Models with smaller boxes demonstrate more reliable performance across diverse musical content.

**Benefit:** Identifies which models provide consistent results versus those with high variance, critical for production deployment where reliability is paramount.

### Runtime vs Performance

**Description:** This efficiency analysis plots processing time against F-measure performance, revealing the computational cost of accuracy. Models in the upper-left quadrant represent the ideal combination of high performance and low computational requirements.

**Benefit:** Enables informed decisions about model selection based on available computational resources and real-time processing requirements.

### Performance Metrics Comparison

**Description:** This bar chart with error bars provides a direct comparison of mean precision, recall, and F-measure across models, with standard deviations indicating performance variability. Clear visual separation between models highlights significant performance differences.

**Benefit:** Offers a comprehensive overview for quick model comparison and selection based on specific metric priorities.

## Image 2: Onset vs Offset Analysis

### Onset vs Offset F-measure

**Description:** This scatter plot examines how well models detect note beginnings versus endings, with the diagonal line representing perfect onset-offset balance. The moderate correlation (0.388) indicates that models with good onset detection don't necessarily excel at offset detection.

**Benefit:** Reveals architectural strengths and weaknesses in temporal note boundary detection, crucial for accurate rhythm and timing transcription.

### Onset vs Offset Precision/Recall

**Description:** These plots separate precision and recall for onset and offset detection, showing whether models are consistently accurate or complete in both temporal aspects. Systematic deviations from the diagonal indicate model-specific biases.

**Benefit:** Provides granular insight into temporal accuracy components, enabling targeted model improvements for specific timing deficiencies.

### Onset/Offset Performance Comparison

**Description:** This grouped bar chart directly compares onset and offset performance metrics across models, with hatched bars clearly distinguishing offset performance. The visualization reveals which models excel at note start versus end detection.

**Benefit:** Enables quick identification of models with balanced temporal detection capabilities versus those specialized in onset or offset accuracy.

### Correlation Heatmap

**Description:** This heatmap visualizes correlations between all onset and offset metrics, revealing strong internal correlations and weaker cross-correlations. The color coding makes relationship strengths immediately apparent.

**Benefit:** Provides comprehensive understanding of metric interdependencies, informing feature selection and model evaluation strategies.

### Onset-Offset Performance Difference

**Description:** This histogram shows the distribution of onset minus offset F-measure differences across models, with the vertical line at zero indicating perfect balance. Positive values indicate better onset detection, negative values better offset detection.

**Benefit:** Quantifies systematic biases in temporal detection, revealing whether models are inherently better at detecting note starts or ends.

## Image 3: Advanced Performance Patterns

### Performance vs Duration Category

**Description:** This line plot reveals how models perform across binned duration categories, showing whether performance degradation is linear or exhibits specific patterns. Different model trajectories indicate varying robustness to audio length.

**Benefit:** Identifies optimal audio length ranges for each model and reveals whether certain models are specialized for short or long compositions.

### Runtime Efficiency Analysis

**Description:** This scatter plot measures efficiency as F-measure per minute of processing time, revealing the computational cost of accuracy. Models with high efficiency provide better performance per unit of computational resource.

**Benefit:** Guides model selection for resource-constrained environments and enables cost-benefit analysis for computational infrastructure planning.

### Precision-Recall Balance

**Description:** This plot examines the precision-recall difference against F-measure, showing whether high-performing models achieve balance or excel through one metric. The horizontal reference line indicates perfect balance.

**Benefit:** Reveals whether model architectures achieve high performance through balanced detection or by optimizing one aspect of accuracy.

### Performance Consistency Analysis

**Description:** This scatter plot positions models based on mean performance versus standard deviation, where the ideal position is high mean with low variance. Models in the upper-left quadrant offer both high performance and reliability.

**Benefit:** Identifies models suitable for production deployment where consistent performance is crucial for user experience.

### Overlap Ratio Distribution

**Description:** These histograms show how each model's overlap ratio measurements are distributed, revealing whether models consistently achieve similar temporal accuracy or exhibit high variability. Narrower distributions indicate more consistent temporal precision.

**Benefit:** Assesses temporal accuracy consistency, crucial for applications requiring precise timing such as real-time performance or music education.

### Model Performance Radar Chart

**Description:** This multi-dimensional visualization simultaneously displays five key performance metrics for each model, creating distinctive performance "fingerprints." The filled areas represent overall capability profiles.

**Benefit:** Provides intuitive comparison of model strengths and weaknesses across multiple dimensions, facilitating holistic model evaluation.

## Image 4: Statistical Summary

### Model Performance Summary Table

**Description:** This comprehensive table presents key statistics for each model including sample sizes, mean performance metrics, and runtime characteristics. The tabular format enables precise numerical comparisons between models.

**Benefit:** Provides exact values for statistical reporting and enables detailed quantitative analysis for research publications.

### Key Metrics Correlation Matrix

**Description:** This heatmap displays correlations between all major performance metrics, revealing strong positive correlations between precision and recall (0.998) and weaker correlations with temporal metrics. Color intensity indicates correlation strength.

**Benefit:** Identifies redundant metrics and reveals unexpected relationships, informing future evaluation framework design and feature selection.

### F-measure Distribution Comparison

**Description:** These density plots show the probability distributions of F-measure scores for each model, revealing whether models have normal distributions or exhibit skewness. Overlapping distributions indicate similar performance ranges.

**Benefit:** Enables statistical testing assumptions validation and provides deeper insight into performance variability than simple means and standard deviations.

### Model Ranking Visualization

**Description:** This inverted bar chart shows model rankings across five key metrics, where lower bars indicate better performance (rank 1 = best). Consistent low bars across metrics indicate overall superior models.

**Benefit:** Provides clear visual ranking that facilitates model selection based on multiple criteria and reveals models that excel in specific areas.

## Statistical Tests for Future Analysis

### 1. Analysis of Variance (ANOVA)

**Purpose:** Test whether mean F-measure differences between models are statistically significant
**Implementation:** One-way ANOVA on F-measure scores grouped by model
**Benefit:** Provides statistical evidence that observed performance differences are not due to random variation

### 2. Pairwise T-tests

**Purpose:** Identify specific model pairs with significant performance differences
**Implementation:** Independent samples t-tests between all model pairs with Bonferroni correction
**Benefit:** Determines which models are statistically distinguishable from each other

### 3. Pearson/Spearman Correlation Tests

**Purpose:** Quantify and test significance of relationships between metrics
**Implementation:** Correlation analysis with p-values for duration vs performance, precision vs recall, etc.
**Benefit:** Provides statistical evidence for claimed relationships and their practical significance

### 4. Regression Analysis

**Purpose:** Model performance predictors and separate correlation from causation
**Implementation:** Multiple linear regression with duration, runtime, and overlap ratio as predictors
**Benefit:** Identifies causal factors affecting performance and quantifies their impact

### 5. Effect Size Calculations

**Purpose:** Measure practical significance of performance differences
**Implementation:** Cohen's d for pairwise comparisons, eta-squared for ANOVA
**Benefit:** Determines whether statistically significant differences are practically meaningful

### 6. Non-parametric Tests

**Purpose:** Validate findings when data doesn't meet normality assumptions
**Implementation:** Kruskal-Wallis test (non-parametric ANOVA) and Mann-Whitney U tests
**Benefit:** Provides robust statistical evidence regardless of distribution assumptions

### 7. Confidence Intervals

**Purpose:** Quantify uncertainty in performance estimates
**Implementation:** Bootstrap confidence intervals for all key metrics
**Benefit:** Provides range of plausible values for true model performance

### 8. Power Analysis

**Purpose:** Determine if sample sizes are adequate for detecting meaningful differences
**Implementation:** Post-hoc power analysis for significant tests
**Benefit:** Validates that conclusions are based on sufficient data rather than underpowered tests

## Research Impact

These visualizations and statistical tests will provide robust evidence for:

-   **Model Architecture Effectiveness:** Quantitative proof of which architectural approaches work best
-   **Performance Trade-offs:** Statistical validation of precision-recall and accuracy-efficiency relationships
-   **Practical Deployment Guidance:** Evidence-based recommendations for model selection in different scenarios
-   **Future Research Directions:** Identification of specific areas where current models fail and need improvement
