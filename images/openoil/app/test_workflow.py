import unittest
import numpy as np
import xarray as xr
from workflow import validate_horizon


class HorizonValidation(unittest.TestCase):
    def dataset(self, statuses):
        data = xr.Dataset({"status": (("trajectory", "time"), np.array(statuses, dtype=float))}, coords={"time": np.array(["2026-11-20T06", "2026-11-20T07", "2026-11-20T08"], dtype="datetime64[h]")})
        data.status.attrs.update(flag_meanings="active stranded", flag_values=[0, 1])
        return data

    def test_complete_stranding_is_a_valid_natural_stop(self):
        params = {"inicio": "2026-11-20T06:00:00", "horas_vazamento": 1, "horas_simuladas": 4}
        result = validate_horizon(self.dataset([[0, 1, np.nan], [0, 0, 1]]), params)
        np.testing.assert_array_equal(result, [0, 1, 2])

    def test_active_missing_and_unreleased_particles_cannot_pass(self):
        params = {"inicio": "2026-11-20T06:00:00", "horas_vazamento": 1, "horas_simuladas": 4}
        for statuses in ([[0, 1, np.nan], [0, 0, 0]], [[0, 1, np.nan], [np.nan, np.nan, np.nan]]):
            with self.subTest(statuses=statuses), self.assertRaises(AssertionError):
                validate_horizon(self.dataset(statuses), params)
        with self.assertRaises(AssertionError):
            validate_horizon(self.dataset([[0, 1, np.nan], [0, 0, 1]]), dict(params, horas_vazamento=3))

    def test_missing_time_steps_are_not_a_natural_stop(self):
        ds = self.dataset([[0, 1, np.nan], [0, 0, 1]]).isel(time=[0, 2])
        with self.assertRaises(AssertionError):
            validate_horizon(ds, {"inicio": "2026-11-20T06:00:00", "horas_vazamento": 1, "horas_simuladas": 4})


if __name__ == "__main__":
    unittest.main()
