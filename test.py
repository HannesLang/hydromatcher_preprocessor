import unittest
import pandas as pd
from scipy.integrate import quad
from scipy.interpolate import interp1d

class TestFunctions(unittest.TestCase):

    def test_calcvol(self):
        dataframe = pd.DataFrame(columns = ['time', 'q'])
        dataframe.loc[len(dataframe)] = [0.0, 0.0]
        dataframe.loc[len(dataframe)] = [3600.0, 1.0]
        dataframe.loc[len(dataframe)] = [7200.0, 1.0]
        dataframe.loc[len(dataframe)] = [10800.0, 0.0]
        qmax, qvol = self.calculatePeakAndVol(dataframe)
        self.assertEqual(7200, qvol)

    def calculatePeakAndVol(self, dataframe):
        """
        creates a cubic interpolation function for the values provided, calculates the integral value and determines the max value.
        :param dataframe: the values to be used
        :return: maxvalue and volume
        """
        qmax = dataframe['q'].max()

        function_cubic = interp1d(dataframe['time'], dataframe['q'], kind='linear')
        integral, err = quad(function_cubic, 0, dataframe['time'].max())
        qvol = int(round(integral))

        return qmax, qvol