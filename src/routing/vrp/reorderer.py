#!/usr/bin/env python3
"""
Trip Site Reorderer

Handles reordering sites within and across day boundaries to satisfy
operating hours constraints.
"""

from typing import List, Tuple, Optional, Callable
from itertools import permutations
from core.site import Site


class TripReorderer:
    """
    Reorders sites to fit within operating hours constraints.

    Uses permutation-based search to find valid orderings that respect
    operating hours while maintaining trip feasibility.
    """

    def __init__(
        self,
        check_site_fits_fn: Callable,
        max_permutation_size: int = 8
    ):
        """
        Initialize reorderer.

        Args:
            check_site_fits_fn: Function to check if a site fits in a day
                Signature: (sites_so_far, new_site, start_location, budget, start_hour) -> (fits, _, _)
            max_permutation_size: Maximum number of sites to permute
        """
        self.check_site_fits_fn = check_site_fits_fn
        self.max_permutation_size = max_permutation_size

    def try_reorder_day(
        self,
        sites_in_day: List[Site],
        new_site: Site,
        start_location: Site,
        day_budget_minutes: int,
        start_hour: int,
        prev_day_sites: Optional[List[Site]] = None,
        next_day_sites: Optional[List[Site]] = None
    ) -> Tuple[bool, List[Site], Optional[List[Site]], Optional[List[Site]]]:
        """
        Try to reorder sites across day boundaries to make them all fit.

        Includes:
        - All sites from previous day (optional)
        - All sites in current day + new site
        - All sites from next day (optional)

        Args:
            sites_in_day: Sites currently in this day
            new_site: New site to add
            start_location: Starting location (usually home base)
            day_budget_minutes: Time budget for the day
            start_hour: Hour when day starts
            prev_day_sites: Sites from previous day (optional)
            next_day_sites: Sites from next day (optional)

        Returns:
            (success, reordered_current_day, moved_to_prev, moved_to_next)
        """
        # Build the pool of sites that can be reordered
        sites_pool = []
        if prev_day_sites:
            for site in prev_day_sites:
                sites_pool.append(('prev', site))
        for site in sites_in_day:
            sites_pool.append(('current', site))
        sites_pool.append(('current', new_site))
        if next_day_sites:
            for site in next_day_sites:
                sites_pool.append(('next', site))

        # Limit permutations to reasonable size
        if len(sites_pool) > self.max_permutation_size:
            # Fall back to simple reordering within current day only
            return self._reorder_within_current_day(
                sites_in_day,
                new_site,
                start_location,
                day_budget_minutes,
                start_hour
            )

        # Try permutations considering day boundaries
        return self._reorder_across_days(
            sites_pool,
            start_location,
            day_budget_minutes,
            start_hour,
            prev_day_sites,
            next_day_sites
        )

    def _reorder_within_current_day(
        self,
        sites_in_day: List[Site],
        new_site: Site,
        start_location: Site,
        day_budget_minutes: int,
        start_hour: int
    ) -> Tuple[bool, List[Site], None, None]:
        """Reorder sites within current day only (simpler case)"""
        all_sites = sites_in_day + [new_site]

        if len(all_sites) > self.max_permutation_size:
            return False, sites_in_day, None, None

        for perm in permutations(all_sites):
            if self._check_permutation_fits(
                list(perm),
                start_location,
                day_budget_minutes,
                start_hour
            ):
                return True, list(perm), None, None

        return False, sites_in_day, None, None

    def _reorder_across_days(
        self,
        sites_pool: List[Tuple[str, Site]],
        start_location: Site,
        day_budget_minutes: int,
        start_hour: int,
        prev_day_sites: Optional[List[Site]],
        next_day_sites: Optional[List[Site]]
    ) -> Tuple[bool, List[Site], Optional[List[Site]], Optional[List[Site]]]:
        """Reorder sites across day boundaries"""
        for perm in permutations(sites_pool):
            # Extract sites for current day from this permutation
            current_day_sites = [site for (day, site) in perm if day == 'current']

            # Check if current day sites fit
            if self._check_permutation_fits(
                current_day_sites,
                start_location,
                day_budget_minutes,
                start_hour
            ):
                # Found a valid ordering!
                # Determine what moved to adjacent days
                moved_to_prev = self._calculate_moved_sites(
                    perm,
                    'prev',
                    prev_day_sites
                )
                moved_to_next = self._calculate_moved_sites(
                    perm,
                    'next',
                    next_day_sites
                )

                return True, current_day_sites, moved_to_prev, moved_to_next

        # No valid ordering found
        return False, [], None, None

    def _check_permutation_fits(
        self,
        sites: List[Site],
        start_location: Site,
        day_budget_minutes: int,
        start_hour: int
    ) -> bool:
        """Check if a permutation of sites fits within the day"""
        for i in range(len(sites)):
            sites_so_far = list(sites[:i])
            site_to_check = sites[i]
            fits, _, _ = self.check_site_fits_fn(
                sites_so_far,
                site_to_check,
                start_location,
                day_budget_minutes,
                start_hour
            )
            if not fits:
                return False
        return True

    def _calculate_moved_sites(
        self,
        permutation: List[Tuple[str, Site]],
        target_day: str,
        original_sites: Optional[List[Site]]
    ) -> Optional[List[Site]]:
        """Calculate which sites moved to a target day"""
        # Can't use set() with dicts, so compare by site name
        original_names = set(
            site.get('site_name', site.get('name', str(site)))
            for site in (original_sites or [])
        )
        new_sites = [site for (day, site) in permutation if day == target_day]
        new_names = set(
            site.get('site_name', site.get('name', str(site)))
            for site in new_sites
        )

        moved_names = new_names - original_names
        moved = [site for site in new_sites
                 if site.get('site_name', site.get('name', str(site))) in moved_names]
        return moved if moved else None
