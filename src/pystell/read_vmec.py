"""
Author: Aaron Bader, UW-Madison 2020

This file provides functionality to read data from a VMEC wout file and 
plot various quantities of interest. It offers versatility for plotting, 
displaying plots, or exporting data.
"""

from netCDF4 import Dataset
import numpy as np
import matplotlib.pyplot as plt
import imp
from matplotlib import cm
from scipy.optimize import fsolve
import scipy.integrate as integrate
import scipy.interpolate as interp
from scipy.optimize import minimize
import logging

try:
    imp.find_module("mayavi")
    use_mayavi = True
    from mayavi import mlab
    import vtk
except ImportError:
    use_mayavi = False


class VMECData:
    """
    A class for reading and storing data from a VMEC wout file and providing methods for
    plotting and analysis.

    Attributes:
    - data (netCDF4.Dataset): The netCDF4 dataset object containing the VMEC data.
    - rmnc (np.ndarray): Array of Fourier coefficients of the Fourier expansion of R.
    - zmns (np.ndarray): Array of Fourier coefficients of the Fourier expansion of Z.
    - lmns (np.ndarray): Array of Fourier coefficients of the Fourier expansion of lambda.
    - bmnc (np.ndarray): Array of Fourier coefficients of the Fourier expansion of B.
    - gmnc (np.ndarray): Array of Fourier coefficients of the Fourier expansion of G.
    - bsubumnc (np.ndarray): Array of Fourier coefficients of the Fourier expansion of bsubu.
    - bsubvmnc (np.ndarray): Array of Fourier coefficients of the Fourier expansion of bsubv.
    - xm (np.ndarray): Array of poloidal mode numbers.
    - xn (np.ndarray): Array of toroidal mode numbers.
    - xmnyq (np.ndarray): Array of poloidal mode numbers for nyquist harmonics.
    - xnnyq (np.ndarray): Array of toroidal mode numbers for nyquist harmonics.
    - raxis (np.ndarray): Array of R values defining the magnetic axis.
    - zaxis (np.ndarray): Array of Z values defining the magnetic axis.
    - nfp (np.ndarray): Number of field periods.
    - ntor (np.ndarray): Number of toroidal modes.
    - mpol (np.ndarray): Poloidal mode number of the axisymmetric component.
    - mnyq (int): Maximum poloidal mode number for nyquist harmonics.
    - nnyq (int): Maximum toroidal mode number for nyquist harmonics.
    - a (np.ndarray): Minor radius of the flux surface.
    - psi (np.ndarray): Poloidal magnetic flux.
    - psips (np.ndarray): Poloidal magnetic flux evaluated at the surface grid points.
    - s (np.ndarray): Normalized flux coordinate (integer grid).
    - shalf (np.ndarray): Normalized flux coordinate (half grid).
    - volume (np.ndarray): Volume enclosed by each flux surface.
    - b0 (np.ndarray): Vacuum toroidal magnetic field on the magnetic axis.
    - volavgB (np.ndarray): Volume average of the magnetic field strength.
    - ns (int): Number of grid points in the poloidal direction.
    - nmn (int): Number of Fourier coefficients.
    - nmnnyq (int): Number of Fourier coefficients for nyquist harmonics.
    - iota (np.ndarray): Rotational transform.
    - hiota (np.ndarray): Rotational transform evaluated at the half grid points.
    - jdotb (np.ndarray): JdotB, where J is the current density and B is the magnetic field.
    - pres (np.ndarray): Plasma pressure.
    - betavol (np.ndarray): Volume-averaged plasma beta.
    - bvco (np.ndarray): Volume-averaged vacuum beta.
    - buco (np.ndarray): Vacuum magnetic energy.
    - aspect (np.ndarray): Aspect ratio of the magnetic geometry.
    - rmax_surf (np.ndarray): Maximum major radius of the surface grid.
    - rmin_surf (np.ndarray): Minimum major radius of the surface grid.
    - zmax_surf (np.ndarray): Maximum vertical position of the surface grid.
    - betaxis (np.ndarray): Plasma beta at the magnetic axis.
    - interpb_at (int): Normalized flux coordinate for last interpolation of B coefficients.
    - binterp (np.ndarray): Array of B coefficients after interpolation.
    - interpr_at (int): Normalized flux coordinate for last interpolation of R coefficients.
    - rinterp (np.ndarray): Array of R coefficients after interpolation.
    - interpz_at (int): Normalized flux coordinate for last interpolation of Z coefficients.
    - zinterp (np.ndarray): Array of Z coefficients after interpolation.
    - interpl_at (int): Normalized flux coordinate for last interpolation of lambda coefficients.
    - linterp (np.ndarray): Array of lambda coefficients after interpolation.
    - iotaspl (CubicSpline): Cubic spline interpolation of rotational transform.
    """

    def __init__(self, fname):
        """
        Initialize a VMECData object by reading data from a VMEC wout file.

        Args:
        - fname: String, path to the VMEC wout file.
        """

        self.data = Dataset(fname)
        self.rmnc = np.array(self.data.variables["rmnc"][:])
        self.zmns = np.array(self.data.variables["zmns"][:])
        self.lmns = np.array(self.data.variables["lmns"][:])
        self.bmnc = np.array(self.data.variables["bmnc"][:])
        self.gmnc = np.array(self.data.variables["gmnc"][:])
        self.bsubumnc = np.array(self.data.variables["bsubumnc"][:])
        self.bsubvmnc = np.array(self.data.variables["bsubvmnc"][:])

        self.xm = np.array(self.data.variables["xm"][:])
        self.xn = np.array(self.data.variables["xn"][:])
        self.xmnyq = np.array(self.data.variables["xm_nyq"][:])
        self.xnnyq = np.array(self.data.variables["xn_nyq"][:])
        self.raxis = np.array(self.data.variables["raxis_cc"][:])
        self.zaxis = np.array(self.data.variables["zaxis_cs"][:])
        self.nfp = np.array(self.data.variables["nfp"])
        self.ntor = np.array(self.data.variables["ntor"])
        self.mpol = np.array(self.data.variables["mpol"])
        self.mnyq = int(max(abs(self.xmnyq)))
        self.nnyq = int(max(abs(self.xnnyq)) / self.nfp)
        self.a = np.array(self.data.variables["Aminor_p"])
        self.psi = np.array(self.data.variables["phi"])
        self.psips = np.array(self.data.variables["phips"])
        self.s = self.psi / self.psi[-1]  # integer grid
        self.shalf = self.s - self.s[1] / 2  # half grid
        self.volume = np.array(self.data.variables["volume_p"])
        self.b0 = np.array(self.data.variables["b0"])
        self.volavgB = np.array(self.data.variables["volavgB"])
        self.ns = len(self.psi)
        self.nmn = len(self.xm)
        self.nmnnyq = len(self.xmnyq)
        self.iota = np.array(self.data.variables["iotaf"])
        self.hiota = np.array(self.data.variables["iotas"])  # half grid
        self.jdotb = np.array(self.data.variables["jdotb"])
        self.pres = np.array(self.data.variables["pres"])
        self.betavol = np.array(self.data.variables["beta_vol"])
        self.bvco = np.array(self.data.variables["bvco"])
        self.buco = np.array(self.data.variables["buco"])

        self.aspect = np.array(self.data.variables["aspect"])
        self.rmax_surf = np.array(self.data.variables["rmax_surf"])
        self.rmin_surf = np.array(self.data.variables["rmin_surf"])
        self.zmax_surf = np.array(self.data.variables["zmax_surf"])
        self.betaxis = np.array(self.data.variables["betaxis"])

        # interpolation stuff
        self.interpb_at = -1
        self.binterp = np.empty(self.nmnnyq)
        self.interpr_at = -1
        self.rinterp = np.empty(self.nmn)
        self.interpz_at = -1
        self.zinterp = np.empty(self.nmn)
        self.interpl_at = -1
        self.linterp = np.empty(self.nmn)

        # splines get filled as needed
        self.iotaspl = None

    def s2fs(self, s, isint=True):
        """
        Convert a normalized flux value s to a flux surface index.

        Args:
        - s: Float, normalized flux value.
        - isint: Boolean, indicates whether to round the result to the nearest integer (default True).

        Returns:
        - fs: Integer or float, flux surface index.
        """

        fs = s * (self.ns - 1)
        if isint:
            fs = int(round(fs))
        return fs

    def fs2s(self, fs):
        """
        Convert a flux surface index (integer or not) into a normalized flux s.

        Args:
        - fs: Integer or float, flux surface index.

        Returns:
        - s: Float, normalized flux value.
        """

        s = float(fs) / (self.ns - 1)
        return s

    def bean_radius_horizontal(self):
        """
        Compute the minor radius by evaluating the outboard and inboard R values.

        Returns:
        - Minor radius: Float, the computed minor radius.
        """

        Rout = 0.0
        Rin = 0.0

        for i in range(len(self.xm)):
            Rout += self.rmnc[-1, i]
            if self.xm[i] % 2 == 1:
                Rin -= self.rmnc[-1, i]
            else:
                Rin += self.rmnc[-1, i]
        return (Rout - Rin) / 2

    # plot a flux surface with flux surface index fs.
    def fsplot(self, phi=0, fs=-1, ntheta=50, plot=True, show=False):
        """
        Plot a flux surface with flux surface index fs.

        Args:
        - phi: Float, toroidal angle (default 0).
        - fs: Integer, flux surface index (default -1).
        - ntheta: Integer, number of points to use for the angular grid (default 50).
        - plot: Boolean, whether to plot the flux surface (default True).
        - show: Boolean, whether to display the plot (default False).

        Returns:
        - r: Float, radial coordinates of the flux surface.
        - z: Float, vertical coordinates of the flux surface.
        """
        theta = np.linspace(0, 2 * np.pi, num=ntheta + 1)

        r = np.zeros(ntheta + 1)
        z = np.zeros(ntheta + 1)
        for i in range(len(self.xm)):
            m = self.xm[i]
            n = self.xn[i]
            angle = m * theta - n * phi
            r += self.rmnc[fs, i] * np.cos(angle)
            z += self.zmns[fs, i] * np.sin(angle)

        if plot:
            plt.plot(r, z)
            plt.axis("equal")
            if show:
                plt.show()
        return r, z

    def mirror(self, s=1.0):
        """
        Calculate the mirror term on a given flux surface by comparing
        the outboard midplane value at phi=0, and the outboard midplane value
        at the half period.  This is the ROSE definition.

        Args:
        - s: Float, normalized flux coordinate (default 1.0).

        Returns:
        - Mirror term: Float, calculated mirror term.
        """

        B1 = self.modb_at_point(s, 0, 0)
        B2 = self.modb_at_point(s, 0, np.pi / self.nfp)
        return (B1 - B2) / (B1 + B2)

    def modb_at_point(self, s, theta, phi):
        """
        Calculate modb at a point.

        Args:
        - s: Float, normalized flux coordinate.
        - theta: Float, poloidal angle.
        - phi: Float, toroidal angle.

        Returns:
        - modb: Float, calculated modb at the specified point.
        """

        self.interp_val(s, fourier="b")
        # remember bmnc is on the half grid
        return sum(self.binterp * np.cos(self.xmnyq * theta - self.xnnyq * phi))

    def modb_on_fieldline(
        self,
        fs,
        phimax=4 * np.pi,
        npoints=1001,
        phistart=0,
        thoffset=0,
        plot=True,
        show=False,):
        """
        Plot modb on a field line starting at the outboard midplane for flux surface index fs.
        This is mostly deprecated and now calls xyz_on_fieldline.

        Args:
        - fs: Integer, flux surface index.
        - phimax: Float, maximum toroidal angle (default 4 * np.pi).
        - npoints: Integer, number of points to compute along the field line (default 1001).
        - phistart: Float, starting toroidal angle (default 0).
        - thoffset: Float, toroidal offset angle (default 0).
        - plot: Boolean, whether to plot the modb (default True).
        - show: Boolean, whether to display the plot (default False).

        Returns:
        - phi: Array, toroidal angle array.
        - modB: Array, modb values along the field line.
        - theta: Array, poloidal angle array.
        """

        s = float(fs) / self.ns
        phi, modB, theta = self.xyz_on_fieldline(
            s,
            thoffset,
            phistart,
            phimax=phimax,
            npoints=npoints,
            invmec=True,
            plot=False,
            onlymodB=True,
        )

        if plot:
            plt.plot(phi, modB)
            if show:
                plt.show()
        return phi, modB, theta

    def xyz_on_fieldline(
        self,
        x,
        y,
        z,
        phimax=4 * np.pi,
        npoints=1001,
        invmec=False,
        inrpz=False,
        retrpz=False,
        plot=True,
        show=False,
        onlymodB=False,
    ):
        """
        Get x, y, z, and modB on a field line, with options to return r, phi, z instead and some plotting options.

        Args:
        - x: Float, starting coordinate x (or r if inrpz is True).
        - y: Float, starting coordinate y (or phi if inrpz is True).
        - z: Float, starting coordinate z (or z if inrpz is True).
        - phimax: Float, maximum toroidal angle to follow (default 4 * np.pi).
        - npoints: Integer, number of points to compute along the field line (default 1001).
        - invmec: Boolean, whether the starting coordinates are in VMEC coordinates (default False).
        - inrpz: Boolean, whether the starting coordinates are in (r, phi, z) format (default False).
        - retrpz: Boolean, whether to return (r, phi, z) instead of (x, y, z) (default False).
        - plot: Boolean, whether to plot the field line (default True).
        - show: Boolean, whether to display the plot (default False).
        - onlymodB: Boolean, whether to return only modB values (default False).

        Returns:
        If retrpz is False:
        - xarr: Array, x coordinates along the field line.
        - yarr: Array, y coordinates along the field line.
        - zarr: Array, z coordinates along the field line.
        - modB: Array, modB values along the field line.

        If retrpz is True:
        - rarr: Array, radial coordinates along the field line.
        - phi: Array, toroidal angle coordinates along the field line.
        - zarr: Array, z coordinates along the field line.
        - modB: Array, modB values along the field line.
        """
        
        if not invmec and not inrpz:
            s, theta, zeta = self.xyz2vmec(x, y, z)
        elif not invmec and inrpz:
            s, theta, zeta = self.rpz2vmec(x, y, z)
        elif invmec and not inrpz:
            s = x
            theta = y
            zeta = z
        else:
            logging.error("Cannot set both invmec and inrpz, silly")
            return

        # interp the rz grids
        self.interp_val(s, fourier="r")
        self.interp_val(s, fourier="z")
        self.interp_val(s, fourier="l")
        self.interp_val(s, fourier="b")

        if self.iotaspl == None:
            self.iotaspl = interp.CubicSpline(self.s, self.iota)
        iota = self.iotaspl(s)
        phi = np.linspace(zeta, zeta + phimax, npoints)
        thetastar = phi * iota + theta
        theta = np.zeros(npoints)
        modB = np.zeros(npoints)
        if not onlymodB:
            rarr = np.zeros(npoints)
            zarr = np.zeros(npoints)

        def theta_solve(x):
            lam = sum(self.linterp * np.sin(self.xm * x - self.xn * phi[i]))
            return x + lam - thetastar[i]

        for i in range(npoints):
            theta[i] = fsolve(theta_solve, thetastar[i])
            modB[i] = sum(
                self.binterp * np.cos(self.xmnyq * theta[i] - self.xnnyq * phi[i])
            )
            angle = self.xm * theta[i] - self.xn * phi[i]
            if not onlymodB:
                rarr[i] = sum(self.rinterp * np.cos(angle))
                zarr[i] = sum(self.zinterp * np.sin(angle))

        if not onlymodB:
            xarr = rarr * np.cos(phi)
            yarr = rarr * np.sin(phi)

        if plot:
            fig = plt.figure()
            ax = fig.add_subplot(111, projection="3d")
            ax.plot(xarr, yarr, zarr)
            if show:
                plt.show()
        if retrpz:
            return rarr, phi, zarr, modB
        if onlymodB:
            return phi, modB, theta
        else:
            return xarr, yarr, zarr, modB

    # FIX: there is an issue with plot display at high resolution
    def modb_on_surface(
        self,
        s=1,
        ntheta=64,
        nphi=64,
        plot=True,
        show=False,
        outxyz=None,
        full=False,
        alpha=1,
        mayavi=True,
        dpi=300,
        ):
        """
        Plot modb on a flux surface with the specified parameters.

        Args:
        - s: Float, normalized flux value specifying the flux surface (default 1).
        - ntheta: Integer, number of points in the theta direction (default 64).
        - nphi: Integer, number of points in the phi direction (default 64).
        - plot: Boolean, whether to plot the surface (default True).
        - show: Boolean, whether to display the plot (default False).
        - outxyz: String, file path to write the x, y, z coordinates of the surface points (default None).
        - full: Boolean, whether to plot the full toroidal domain (default False).
        - alpha: Float, transparency of the surface plot (default 1).
        - mayavi: Boolean, whether to use Mayavi for plotting (default True).
        - dpi: Integer, resolution of the plot (default 300).

        Returns:
        - List containing arrays of x, y, z, and modB values on the surface.
        """
        
        # first attempt will use trisurface, let's see how it looks
        r = np.zeros([nphi, ntheta])
        z = np.zeros([nphi, ntheta])
        x = np.zeros([nphi, ntheta])
        y = np.zeros([nphi, ntheta])
        b = np.zeros([nphi, ntheta])

        if full:
            divval = 1
        else:
            divval = self.nfp

        theta = np.linspace(0, 2 * np.pi, num=ntheta)
        phi = np.linspace(0, 2 * np.pi / divval, num=nphi)

        for phii in range(nphi):
            p = phi[phii]
            for ti in range(ntheta):
                th = theta[ti]
                r[phii, ti] = self.r_at_point(s, th, p)
                z[phii, ti] = self.z_at_point(s, th, p)
                x[phii, ti] += r[phii, ti] * np.cos(p)
                y[phii, ti] += r[phii, ti] * np.sin(p)
                b[phii, ti] = self.modb_at_point(s, th, p)

        my_col = cm.jet((b - np.min(b)) / (np.max(b) - np.min(b)))

        if plot and (not use_mayavi or not mayavi):
            fig = plt.figure(dpi=dpi)
            ax = fig.add_subplot(111, projection="3d")
            # my_col = cm.jet((b-np.min(b))/(np.max(b)-np.min(b)))

            ax.plot_surface(x, y, z, facecolors=my_col, norm=True, alpha=alpha)
            # set axis to equal
            max_range = (
                np.array(
                    [x.max() - x.min(), y.max() - y.min(), z.max() - z.min()]
                ).max()
                / 2.0
            )

            mid_x = (x.max() + x.min()) * 0.5
            mid_y = (y.max() + y.min()) * 0.5
            mid_z = (z.max() + z.min()) * 0.5
            ax.set_xlim(mid_x - max_range, mid_x + max_range)
            ax.set_ylim(mid_y - max_range, mid_y + max_range)
            ax.set_zlim(mid_z - max_range, mid_z + max_range)

            if show:
                plt.show()

        elif plot and use_mayavi and mayavi:
            mlab.figure(bgcolor=(1.0, 1.0, 1.0), size=(800, 600))
            mlab.contour3d(x, y, z, b)
            if show:
                mlab.show()

        if outxyz is not None:
            wf = open(outxyz, "w")
            for phii in range(nphi):
                for ti in range(ntheta):
                    s = (
                        str(x[phii, ti])
                        + "\t"
                        + str(y[phii, ti])
                        + "\t"
                        + str(z[phii, ti])
                        + "\n"
                    )
                    wf.write(s)
        return [x, y, z, b]

    def axis(self, phi):
        """
        Calculate the position of the magnetic axis at the specified toroidal angle.

        Args:
        - phi: Float, toroidal angle.

        Returns:
        - r: Float, Radial coordinate of the magnetic axis.
        - z: Float, Vertical coordinate of the magnetic axis.
        """
        
        r = 0
        z = 0
        for i in range(len(self.raxis)):
            r += self.raxis[i] * np.cos(i * self.nfp * phi)
            z += self.zaxis[i] * np.sin(i * self.nfp * phi)
        return r, z

    def plot_iota(self, plot=True, show=False):
        """
        Plot the rotational transform as a function of normalized flux.

        Args:
        - plot: Boolean, whether to plot the data (default True).
        - show: Boolean, whether to display the plot (default False).

        Returns:
        - s: Array, normalized flux values.
        - iota: Array, rotational transform values.
        """
        
        s = self.psi[1:] / self.psi[-1]
        if plot:
            plt.plot(s, self.iota[1:])
            if show:
                plt.show()
        return s, self.iota[1:]

    def pressure(self, plot=True, show=False):
        """
        Plot the pressure profile as a function of normalized flux.

        Args:
        - plot: Boolean, whether to plot the data (default True).
        - show: Boolean, whether to display the plot (default False).

        Returns:
        - s: Array, normalized flux values.
        - pres: Array, pressure profile values.
        """
        
        s = self.psi[1:] / self.psi[-1]
        pres = self.pres[1:]
        if plot:
            plt.plot(s, pres)
            if show:
                plt.show()
        return s, pres

    def current(self, plot=True, show=False):
        """
        Plot the current profile as a function of normalized flux.

        Args:
        - plot: Boolean, whether to plot the data (default True).
        - show: Boolean, whether to display the plot (default False).

        Returns:
        - s: Array, normalized flux values.
        - jdotb: Array, current profile values.
        """
        
        s = self.psi[1:] / self.psi[-1]
        jdotb = self.jdotb[1:]
        if plot:
            plt.plot(s, jdotb)
            if show:
                plt.show()
        return s, jdotb

    def r_at_point(self, s, theta, phi):
        """
        Calculate the radial coordinate at a given point on a flux surface.

        Args:
        - s: Normalized flux value.
        - theta: Poloidal angle.
        - phi: Toroidal angle.

        Returns:
        - Radial coordinate at the specified point.
        """
        
        self.interp_val(s, fourier="r")
        return sum(self.rinterp * np.cos(self.xm * theta - self.xn * phi))

    def z_at_point(self, s, theta, phi):
        """
        Calculate the vertical coordinate at a given point on a flux surface.

        Args:
        - s: Float, Normalized flux value.
        - theta: Float, Poloidal angle.
        - phi: Float, Toroidal angle.

        Returns:
        - Vertical coordinate at the specified point.
        """
        
        self.interp_val(s, fourier="z")
        return sum(self.zinterp * np.sin(self.xm * theta - self.xn * phi))

    def interp_half(self, val, s, mn):
        """
        Perform interpolation on the half grid.

        Args:
        - val: Array, values to be interpolated.
        - s: Float, Normalized flux value.
        - mn: Integer, Mode number.

        Returns:
        - Interpolated value at the specified flux surface and mode number.
        """
        
        if s < self.shalf[1]:
            v = val[1, mn]
        elif s > self.shalf[-1]:
            v = val[-1, 0]
        else:
            vfunc = interp.interp1d(self.shalf, val[:, mn])
            v = vfunc(s)
        return v

    # return dvds, the volume derivative, which is 4 pi^2 abs(g_00).
    def dvds(self, s, interpolate=False):
        """
        Calculate the volume derivative with respect to normalized flux s.

        Args:
        - s: Float, Normalized flux value.
        - interpolate: Boolean, flag indicating whether to interpolate the values (default False).

        Returns:
        - dvds: Float, Volume derivative at the specified flux surface.
        """
        
        if not interpolate:
            # if we don't want to interpolate, then get an actual value
            fs = self.s2fs(s)
            g = self.gmnc[fs, 0]
        else:
            g = self.interp_half(self.gmnc, s, 0)

        dvds_val = abs(4 * np.pi**2 * g)
        return dvds_val

    def well(self, s):
        """
        Calculate the well function at a given normalized flux s.

        Args:
        - s: Float, Normalized flux value.

        Returns:
        - bsq: Float, The average of B^2 over the flux surface.
        """
        # interpolate for bmn and gmn
        bslice = np.empty(self.nmn)
        gslice = np.empty(self.nmn)
        for mn in range(self.nmn):
            bslice[mn] = self.interp_half(self.bmnc, s, mn)
            gslice[mn] = self.interp_half(self.gmnc, s, mn)

        vol = 4 * np.pi**2 * abs(gslice[0])

        def bsqfunc(th, ze):
            b = 0
            for mn in range(self.nmn):
                b += bslice[mn] * np.cos(self.xm[mn] * th - self.xn[mn] * ze)
            return b * b

        def gfunc(th, ze):
            g = 0
            for mn in range(self.nmn):
                g += gslice[mn] * np.cos(self.xm[mn] * th - self.xn[mn] * ze)
            return abs(g)

        def bsqg(th, ze):
            return bsqfunc(th, ze) * gfunc(th, ze)

        # get flux surface average B**2
        val, err = integrate.dblquad(
            bsqg, 0, 2 * np.pi, lambda x: 0, lambda x: 2 * np.pi
        )
        return val / vol

    # simple vacuum well, uses B_00 as <B> which isn't quite right
    def well_simp(self, s, plot=True, show=False):
        """
        Calculate the well function using simplified interpolation.

        Args:
        - s: Normalized flux value.
        - plot: Whether to plot the results.
        - show: Whether to display the plot.

        Returns:
        - Tuple of CubicSpline objects: (b00_spl, db00_spl, vol_spl, g00_spl).
        """
        
        b00_spl = interp.CubicSpline(self.shalf, self.bmnc[:, 0])
        g00_spl = interp.CubicSpline(self.shalf, 4 * np.pi**2 * abs(self.gmnc[:, 0]))
        vol_spl = g00_spl.antiderivative()
        db00_spl = b00_spl.derivative()

        if plot:
            svals = np.linspace(0, 1, 51)
            fig, axs = plt.subplots(2, 2, figsize=(12, 8))

            axs[0, 0].plot(svals, b00_spl(svals))
            axs[0, 0].set_title('b00_spl')

            axs[0, 1].plot(svals, db00_spl(svals))
            axs[0, 1].set_title('db00_spl')

            axs[1, 0].plot(svals, vol_spl(svals))
            axs[1, 0].set_title('vol_spl')

            axs[1, 1].plot(svals, g00_spl(svals))
            axs[1, 1].set_title('g00_spl')

            plt.tight_layout()
            if show:
                plt.show()
        return (b00_spl, db00_spl, vol_spl, g00_spl)

    def interp_val(self, s, fourier="b"):
        """
        Interpolate values on the given flux surface.

        Args:
        - s: Float, Normalized flux value.
        - fourier: str, Type of Fourier component to interpolate ("b", "r", "z", or "l") (default: "b").

        Raises:
        - ValueError: If fourier is not one of "b", "r", "z", or "l".
        """
        if fourier == "b":
            if self.interpb_at == s:
                return
            for i in range(self.nmnnyq):
                bspl = interp.CubicSpline(self.shalf, self.bmnc[:, i])
                self.interpb_at = s
                self.binterp[i] = bspl(s)
        elif fourier == "r":
            if self.interpr_at == s:
                return
            for i in range(self.nmn):
                bspl = interp.CubicSpline(self.s, self.rmnc[:, i])
                self.interpr_at = s
                self.rinterp[i] = bspl(s)
        elif fourier == "z":
            if self.interpz_at == s:
                return
            for i in range(self.nmn):
                bspl = interp.CubicSpline(self.s, self.zmns[:, i])
                self.interpz_at = s
                self.zinterp[i] = bspl(s)
        elif fourier == "l":
            if self.interpl_at == s:
                return
            for i in range(self.nmn):
                bspl = interp.CubicSpline(self.s, self.lmns[:, i])
                self.interpl_at = s
                self.linterp[i] = bspl(s)
        else:
            raise ValueError("fourier must be 'b', 'r', 'z', or 'l'")


    def vmec2rpz(self, s, theta, zeta):
        """
        Convert VMEC coordinates to cylindrical coordinates.

        Args:
        - s: Float, Normalized flux value.
        - theta: Float, Poloidal angle.
        - zeta: Float, Toroidal angle.

        Returns:
        - r: Float, Radial coordinate.
        - z: Float, Vertical coordinate.
        """
        # interpolate the rmnc, and zmns arrays
        if self.interpr_at != s:
            self.interp_val(s, fourier="r")
        if self.interpz_at != s:
            self.interp_val(s, fourier="z")

        angle = self.xm * theta - self.xn * zeta
        r = sum(self.rinterp * np.cos(angle))
        z = sum(self.zinterp * np.sin(angle))

        return r, z

    def vmec2xyz(self, s, theta, zeta):
        """
        Convert VMEC coordinates to Cartesian coordinates.

        Args:
        - s: Float, Normalized flux value.
        - theta: Float, Poloidal angle.
        - zeta: Float, Toroidal angle.

        Returns:
        - x: Float, Cartesian x-coordinate.
        - y: Float, Cartesian y-coordinate.
        - z: Float, Cartesian z-coordinate.
        """
        
        r, phi, z = self.vmec2rpz(s, theta, zeta)
        x = r * np.cos(phi)
        y = r * np.sin(phi)
        return x, y, z

    def xyz2vmec(self, x, y, z):
        """
        Convert Cartesian coordinates to VMEC coordinates.

        Args:
        - x: Float, Cartesian x-coordinate.
        - y: Float, Cartesian y-coordinate.
        - z: Float, Cartesian z-coordinate.

        Returns:
        - VMEC coordinates [s, theta, zeta].
        """
        
        r = np.sqrt(x**2 + y**2)
        phi = np.arctan2(y, x)
        return self.rpz2vmec(r, phi, z)

    def rpz2vmec(self, r, phi, z):
        """
        Convert cylindrical coordinates to VMEC coordinates.

        Args:
        - r: Float, Radial distance.
        - phi: Float, Azimuthal angle.
        - z: Float, Vertical distance.

        Returns:
        - VMEC coordinates [s, theta, zeta].
        """
        vmec_vec = np.empty(3)
        vmec_vec[2] = phi
        # we don't know what flux surface we're on so we can't really
        # make use of the lambda variable
        thguess = self.thetaguess(r, phi, z)
        vmec_vec[0] = self.sguess(r, phi, z, thguess)
        vmec_vec[1] = thguess

        # this function takes a numpy array vmec_coords
        # and returns a float representing the difference
        def solve_function(vmec_coords):

            vmec_coords[0] = abs(vmec_coords[0])
            rg, pg, zg = self.vmec2rpz(vmec_coords[0], vmec_coords[1], vmec_coords[2])
            # p is by definition correct, so we just look at r and z
            ans = 0
            ans += (r - rg) ** 2
            # ans += (y-yg)**2
            ans += (z - zg) ** 2
            return np.sqrt(ans)

        # set bounds for s, theta and zeta
        bounds = (
            (0.0, 1.0),
            (vmec_vec[1] - np.pi / 2, vmec_vec[1] + np.pi / 2),
            (vmec_vec[2] - 0.001, vmec_vec[2] + 0.001),
        )

        sol = minimize(
            solve_function, vmec_vec, method="L-BFGS-B", tol=1.0e-8, bounds=bounds
        )

        s = sol.x[0]
        mins = 1.0 / (self.ns * 3)
        maxs = 1.0 - mins
        if s < mins:
            logging.warning("s value of %.4f is too low, answer may be incorrect", s)
        if s > maxs:
            logging.warning("s value of %.4f is too high, answer may be incorrect", s)

        return sol.x

    def thetaguess(self, r, phi, z):
        """
        Guess the value of theta based on cylindrical coordinates.

        Args:
        - r: Float, Radial distance.
        - phi: Float, Azimuthal angle.
        - z: Float, Vertical distance.

        Returns:
        - Guessed value of theta.
        """
        r0, phi0, z0 = self.vmec2rpz(0, 0, phi)
        r1, phi1, z1 = self.vmec2rpz(1, 0, phi)

        # get relative r and z for plasma and our point
        r_pl = r1 - r0
        z_pl = z1 - z0

        r_pt = r - r0
        z_pt = z - z0

        # get theta for plasma and our point
        th_pl = np.arctan2(z_pl, r_pl)
        th_pt = np.arctan2(z_pt, r_pt)

        return th_pt - th_pl

    def sguess(self, r, phi, z, theta, r0=None, z0=None):
        """
        Guess the value of s based on cylindrical coordinates.

        Args:
        - r: Float, Radial distance.
        - phi: Float, Azimuthal angle.
        - z: Float, Vertical distance.
        - theta: Float, Poloidal angle.
        - r0 (optional): Float, Radial distance of the magnetic axis. If None, it will be calculated.
        - z0 (optional): Float, Vertical distance of the magnetic axis. If None, it will be calculated.

        Returns:
        - Guessed value of s.
        """
        # if axis is not around, get it
        if r0 is None:
            r0, phi0, z0 = self.vmec2rpz(0, 0, phi)

        # get r and z at lcfs
        r1, phi1, z1 = self.vmec2rpz(1, theta, phi)

        # squared distances for plasma minor radius and our point at theta
        d_pl = (r1 - r0) ** 2 + (z1 - z0) ** 2
        d_pt = (r - r0) ** 2 + (z - z0) ** 2

        # s guess is normalized radius squared
        return d_pt / d_pl
