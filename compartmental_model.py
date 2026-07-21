"""
The deterministic half of this project: a global SIR/SEIR model with no
geography at all -- one population, solved with RK4. This answers "what
does transmission look like in aggregate" (R0, herd immunity threshold,
how incubation length reshapes the epidemic curve). It cannot represent
where an outbreak is on a map, which is what network_model.py is for.
"""


class CompartmentalResult:
    """Plain container for the output of a compartmental run."""

    def __init__(self, t, S, I, R, E, r0, herd_immunity_threshold,
                 peak_infected, peak_day, final_attack_rate):
        self.t = t
        self.S = S
        self.I = I
        self.R = R
        self.E = E  # None for SIR, a list for SEIR
        self.r0 = r0
        self.herd_immunity_threshold = herd_immunity_threshold
        self.peak_infected = peak_infected
        self.peak_day = peak_day
        self.final_attack_rate = final_attack_rate


class CompartmentalModel:
    """
    Deterministic SIR or SEIR model.

    model_type: "sir" or "seir"
    beta:  transmission rate
    gamma: recovery rate (1 / infectious period)
    sigma: incubation rate (1 / incubation period). Required for SEIR.
    """

    def __init__(self, model_type="sir", beta=0.4, gamma=0.1, sigma=None):
        if model_type not in ("sir", "seir"):
            raise ValueError("model_type must be 'sir' or 'seir'")
        if model_type == "seir" and sigma is None:
            raise ValueError("SEIR needs sigma (1 / incubation period)")

        self.model_type = model_type
        self.beta = beta
        self.gamma = gamma
        self.sigma = sigma

    def r0(self):
        return self.beta / self.gamma

    def herd_immunity_threshold(self):
        r0 = self.r0()
        return 0.0 if r0 <= 1 else 1 - 1 / r0

    def _sir_derivative(self, S, I, R):
        dS = -self.beta * S * I
        dI = self.beta * S * I - self.gamma * I
        dR = self.gamma * I
        return dS, dI, dR

    def _seir_derivative(self, S, E, I, R):
        dS = -self.beta * S * I
        dE = self.beta * S * I - self.sigma * E
        dI = self.sigma * E - self.gamma * I
        dR = self.gamma * I
        return dS, dE, dI, dR

    def _rk4_step_sir(self, S, I, R, dt):
        k1_S, k1_I, k1_R = self._sir_derivative(S, I, R)
        k2_S, k2_I, k2_R = self._sir_derivative(S + dt/2*k1_S, I + dt/2*k1_I, R + dt/2*k1_R)
        k3_S, k3_I, k3_R = self._sir_derivative(S + dt/2*k2_S, I + dt/2*k2_I, R + dt/2*k2_R)
        k4_S, k4_I, k4_R = self._sir_derivative(S + dt*k3_S, I + dt*k3_I, R + dt*k3_R)
        new_S = S + dt/6 * (k1_S + 2*k2_S + 2*k3_S + k4_S)
        new_I = I + dt/6 * (k1_I + 2*k2_I + 2*k3_I + k4_I)
        new_R = R + dt/6 * (k1_R + 2*k2_R + 2*k3_R + k4_R)
        return new_S, new_I, new_R

    def _rk4_step_seir(self, S, E, I, R, dt):
        k1_S, k1_E, k1_I, k1_R = self._seir_derivative(S, E, I, R)
        k2_S, k2_E, k2_I, k2_R = self._seir_derivative(
            S + dt/2*k1_S, E + dt/2*k1_E, I + dt/2*k1_I, R + dt/2*k1_R)
        k3_S, k3_E, k3_I, k3_R = self._seir_derivative(
            S + dt/2*k2_S, E + dt/2*k2_E, I + dt/2*k2_I, R + dt/2*k2_R)
        k4_S, k4_E, k4_I, k4_R = self._seir_derivative(
            S + dt*k3_S, E + dt*k3_E, I + dt*k3_I, R + dt*k3_R)
        new_S = S + dt/6 * (k1_S + 2*k2_S + 2*k3_S + k4_S)
        new_E = E + dt/6 * (k1_E + 2*k2_E + 2*k3_E + k4_E)
        new_I = I + dt/6 * (k1_I + 2*k2_I + 2*k3_I + k4_I)
        new_R = R + dt/6 * (k1_R + 2*k2_R + 2*k3_R + k4_R)
        return new_S, new_E, new_I, new_R

    def run(self, days=200, dt=0.5, vaccinated_frac=0.0, i0_frac=0.001):
        n_steps = int(days / dt)
        t_values, S_values, I_values, R_values = [], [], [], []
        E_values = [] if self.model_type == "seir" else None

        S = 1.0 - i0_frac - vaccinated_frac
        I = i0_frac
        R = vaccinated_frac
        E = 0.0

        t = 0.0
        t_values.append(t); S_values.append(S); I_values.append(I); R_values.append(R)
        if self.model_type == "seir":
            E_values.append(E)

        for _ in range(n_steps):
            if self.model_type == "sir":
                S, I, R = self._rk4_step_sir(S, I, R, dt)
            else:
                S, E, I, R = self._rk4_step_seir(S, E, I, R, dt)

            S = max(S, 0.0)
            I = max(I, 0.0)
            R = max(R, 0.0)
            if self.model_type == "seir":
                E = max(E, 0.0)
                total = S + E + I + R
            else:
                total = S + I + R
            if total > 0:
                S, I, R = S / total, I / total, R / total
                if self.model_type == "seir":
                    E = E / total

            t += dt
            t_values.append(t); S_values.append(S); I_values.append(I); R_values.append(R)
            if self.model_type == "seir":
                E_values.append(E)

        peak_index = max(range(len(I_values)), key=lambda i: I_values[i])

        return CompartmentalResult(
            t=t_values, S=S_values, I=I_values, R=R_values, E=E_values,
            r0=self.r0(),
            herd_immunity_threshold=self.herd_immunity_threshold(),
            peak_infected=I_values[peak_index],
            peak_day=t_values[peak_index],
            final_attack_rate=R_values[-1] - vaccinated_frac,
        )
