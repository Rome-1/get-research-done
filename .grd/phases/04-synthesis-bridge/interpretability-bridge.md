# Bridge Note: Manifold Analysis Methods and Mechanistic Interpretability

## 1. Motivation

Recent work in mechanistic interpretability (ICLR 2025, Anthropic 2024-2025) has established that features in neural networks are not merely single directions in activation space but unfold across multiple directions as **manifold structures** — curves, surfaces, tori, Swiss rolls, and hierarchical trees. This creates a direct need for the mathematical tools surveyed in this project.

Key empirical observations:
- Features in language models form manifolds of dimension d ~ 1-50 in activation spaces of dimension D ~ 10²-10⁴
- Cosine similarity encodes intrinsic geometry through shortest on-manifold paths
- Different layers exhibit different intrinsic dimensionality (ID increases then decreases through network depth)
- The manifold structure of representations predicts generalization: networks that generalize transform data into low-dimensional (but not necessarily flat) manifolds

---

## 2. Specific, Actionable Connections

### Connection 1: Heat Kernel Probing for Feature Manifold Characterization

**The idea:** Apply JMS heat triangulation (Theorem 3) to neural network activation spaces to obtain provably bi-Lipschitz local coordinate systems on feature manifolds.

**Why this works:**
- Neural network activations at a given layer form a point cloud in ℝ^D (D = hidden dimension)
- Feature manifolds are submanifolds of this activation space
- JMS Theorem 3 requires only d reference points and a time parameter t to construct local coordinates
- The bi-Lipschitz guarantee means distances in the coordinate system faithfully represent distances on the manifold — crucial for interpreting which inputs activate "nearby" features

**Concrete protocol:**
1. Collect N activation vectors from a specific layer for inputs sharing a feature (e.g., "mentions of Paris" or "code with recursion")
2. Estimate intrinsic dimension d via local PCA eigenvalue gap
3. Choose d reference activations that span d independent directions
4. Compute heat kernel K_t(x, y_i) for each activation x and reference point y_i, with t = c · R² (R = local scale)
5. The map x → (K_t(x, y₁), ..., K_t(x, y_d)) provides bi-Lipschitz local coordinates

**What you get that you can't get from t-SNE/UMAP:**
- **Guaranteed distance preservation** (both upper and lower bounds, not just qualitative neighborhood preservation)
- **Scale control** via time parameter t (multiscale analysis of feature structure)
- **Quantitative comparison** between features: if two feature manifolds have different JMS constants, their geometric complexity differs in a precise, measurable way
- **Composability:** Local bi-Lipschitz charts can be combined into an atlas, enabling rigorous global analysis

**Practical considerations:**
- For typical mechanistic interpretability datasets (N ~ 10³-10⁵, D ~ 10²-10⁴, d ~ 1-20), sparse spectral methods are fully tractable at O(Nkd)
- The main challenge is reference point selection — Theorem 3 requires d linearly independent directions, which can be obtained from local PCA

### Connection 2: Diffusion Maps for Density-Independent Feature Geometry

**The idea:** Use diffusion maps with α=1 normalization to map the intrinsic geometry of feature manifolds independently of how frequently different feature values are activated.

**Why this matters for interpretability:**
- Neural networks are trained on data with highly non-uniform distributions
- Some feature values (e.g., common words, frequent code patterns) produce far more activation vectors than rare ones
- Standard analysis (including PCA, t-SNE, UMAP) conflates the **geometry** of the feature manifold with the **frequency** of activation
- Diffusion maps with α=1 provably separate these: the resulting embedding reflects only the Riemannian geometry of the manifold, not the density of points on it

**Concrete protocol:**
1. Collect activations from a specific layer
2. Build k-NN graph with Gaussian kernel weights
3. Apply α=1 normalization: K^(1)(x,y) = K(x,y) / (q(x)·q(y)) where q(x) = ∫K(x,y)dμ(y)
4. Normalize to Markov matrix P and compute eigenvectors
5. Diffusion map Ψ_t(x) = (λ₁ᵗψ₁(x), ..., λ_dᵗψ_d(x))

**What you learn:**
- **True feature geometry** independent of training data distribution
- **Multiscale structure:** Varying t reveals feature organization at different scales — coarse semantic categories at large t, fine-grained distinctions at small t
- **Diffusion distance** between activations as a principled metric for "how different are these feature values?" that factors out activation frequency
- **Eigenvalue decay** as a signature of manifold complexity (fast decay = simple manifold, slow decay = complex geometry)

**Application example:** For a "number representation" feature in a language model:
- At large t: reveals coarse structure (positive vs negative, small vs large)
- At small t: reveals fine structure (individual number representations, arithmetic relationships)
- Density independence ensures the representation of "1" (very common) and "1729" (very rare) are treated geometrically, not by frequency

### Connection 3: Persistent Homology for Feature Manifold Topology Classification

**The idea:** Use persistent homology to classify the topology of feature manifolds — are they linear subspaces, circles, spheres, tori, or more complex structures?

**Why this matters:**
- The topology of a feature manifold constrains what the feature can represent
- A circular manifold (H₁ ≠ 0) indicates a periodic feature (time of day, compass direction, cyclic grammar)
- A spherical manifold (H₂ ≠ 0) indicates two independent periodic features
- A tree-like manifold indicates hierarchical organization
- Knowing the topology tells you the **type** of information encoded, not just its dimensionality

**Concrete protocol:**
1. Collect feature activations, reduce dimension via PCA to D' ~ 50 (preserving topology)
2. Compute Vietoris-Rips persistence diagrams for H₀, H₁, H₂
3. Persistent features (far from diagonal) indicate genuine topological structure
4. Compare persistence diagrams across features to classify feature types

**What you learn:**
- **Feature type classification:** β₀ = 1 (connected), β₁ = 1 (circular = periodic feature), β₁ = 2, β₂ = 1 (torus = two independent periodic features)
- **Robustness assessment:** High persistence = robust feature structure, low persistence = noisy or fragile feature
- **Cross-layer tracking:** How does the topology of a feature's manifold change across layers? (Emergence, refinement, or collapse of structure)

---

## 3. Open Problems at the Intersection

### 3.1 Automatic Reference Point Selection for JMS in Activation Spaces

**Problem:** JMS Theorem 3 requires d reference points along linearly independent directions. How to select these automatically from activation data?

**Why it matters:** Without automatic selection, the JMS framework requires human intervention that doesn't scale to analyzing thousands of features across hundreds of layers.

**Possible approach:** Use local PCA to identify d principal directions at each point, then select reference points along these directions at distance c₅R_z. This is implementable but its optimality (and the sensitivity to the choice) is unstudied.

### 3.2 Multi-Manifold Detection in Shared Activation Spaces

**Problem:** Real neural network layers contain multiple overlapping feature manifolds in the same D-dimensional space. How to simultaneously detect, separate, and characterize these manifolds?

**Why it matters:** A single layer may encode dozens of features, each forming its own manifold. Current methods assume a single manifold or require pre-separation (e.g., via sparse autoencoders).

**Connection to survey:** None of the surveyed methods directly addresses multi-manifold detection. The combination of persistent homology (to detect the number of manifolds via H₀ at appropriate scale) with local dimension estimation (to characterize each) is a possible pipeline, but no theoretical analysis exists for this combined approach.

### 3.3 Scalable Bi-Lipschitz Embeddings

**Problem:** The JMS bi-Lipschitz guarantee is the strongest known, but it applies to local patches. For N > 10⁶, even computing the sparse graph becomes expensive. Can we achieve approximate bi-Lipschitz embeddings at sublinear cost?

**Status:** Open. No published work provides subquadratic algorithms with bi-Lipschitz guarantees.

### 3.4 Feature Manifold Evolution During Training

**Problem:** How do feature manifolds form, change topology, and stabilize during training? What is the "manifold formation dynamics" in representation learning?

**Why it matters:** Understanding when and how manifold structure emerges could inform training efficiency, architecture design, and interpretability timing.

**Connection to survey:** Diffusion maps' multiscale property (varying t) could track manifold structure at different stages of training, providing a principled lens for studying representation learning dynamics.

### 3.5 Manifold Curvature and Model Capacity

**Problem:** Is there a relationship between the curvature of feature manifolds and the model's representational capacity or generalization ability?

**Why it matters:** If high-curvature manifolds indicate more complex representations, curvature could serve as a diagnostic for model capacity utilization.

**Connection to survey:** CA-PCA (2024) provides curvature estimates from local data. Combining this with the JMS framework (whose constants depend on metric smoothness C^α) could provide a principled curvature-capacity theory.

### 3.6 Bridging SAE Features and Manifold Geometry

**Problem:** Sparse autoencoders (SAEs) identify discrete features as directions. Feature manifolds suggest continuous, nonlinear structure. What is the precise relationship between SAE features and the geometry of the underlying manifold?

**Why it matters:** This is a foundational question for mechanistic interpretability — are SAE features tangent vectors to manifolds, sections of a fiber bundle, or something else entirely?

**Possible formal framework:** Treat SAE features as approximate tangent vectors at specific points on the feature manifold. The JMS theorem then provides the connection: d tangent directions at a point define a local coordinate system via heat kernels. SAE features may be estimating precisely these tangent directions.

---

## 4. Recommended Research Program

### Near-term (implementable now):
1. **Benchmark JMS vs t-SNE/UMAP** on known synthetic manifolds embedded in high dimensions — quantify the distance preservation advantage
2. **Apply diffusion maps (α=1) to transformer activations** from open models (GPT-2, Pythia) — compare geometry to existing analyses using cosine similarity
3. **Compute persistence diagrams for known feature manifolds** (number features, position features, color features) — validate topology matches expectations

### Medium-term (requires new methods):
4. **Develop automatic JMS reference point selection** for activation spaces
5. **Build multi-manifold detection pipeline** combining PH + local PCA + spectral methods
6. **Track manifold evolution during training** using diffusion map eigenvalue spectra

### Long-term (open theory):
7. **Scalable bi-Lipschitz embeddings** — fundamental algorithmic question
8. **Manifold curvature ↔ model capacity theory** — requires new mathematical framework
9. **SAE-manifold correspondence theorem** — formalizing the feature-as-tangent-vector hypothesis
