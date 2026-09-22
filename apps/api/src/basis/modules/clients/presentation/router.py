"""Client management HTTP endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from basis.modules.clients.application.use_cases import (
    AssessClientSuitabilityCommand,
    ListClientsQuery,
    RegisterClientCommand,
    UpdateClientDetailsCommand,
)
from basis.modules.clients.domain.models import UNSET
from basis.modules.clients.domain.value_objects import ClientStatus
from basis.modules.clients.presentation.dependencies import (
    ArchiveClientDep,
    AssessSuitabilityDep,
    GetClientDep,
    ListClientsDep,
    ReactivateClientDep,
    RegisterClientDep,
    UpdateClientDep,
)
from basis.modules.clients.presentation.schemas import (
    AssessSuitabilityRequest,
    ClientListResponse,
    ClientResponse,
    RegisterClientRequest,
    SuitabilityResponse,
    UpdateClientRequest,
)
from basis.modules.identity.presentation.dependencies import CurrentUserDep, ManagerDep

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get(
    "",
    response_model=ClientListResponse,
    summary="List clients with search, status filter and cursor pagination",
)
async def list_clients(
    use_case: ListClientsDep,
    user: CurrentUserDep,
    query: Annotated[str | None, Query(max_length=120)] = None,
    status_filter: Annotated[ClientStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
) -> ClientListResponse:
    page = await use_case.execute(
        ListClientsQuery(query=query, status=status_filter, limit=limit, cursor=cursor)
    )
    return ClientListResponse.from_page(page)


@router.post(
    "",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new client",
)
async def register_client(
    payload: RegisterClientRequest,
    use_case: RegisterClientDep,
    user: ManagerDep,
) -> ClientResponse:
    view = await use_case.execute(
        RegisterClientCommand(
            name=payload.name,
            email=payload.email,
            tax_id=payload.tax_id,
            notes=payload.notes,
            suitability_answers=payload.suitability_answers,
        )
    )
    return ClientResponse.from_view(view)


@router.get("/{client_id}", response_model=ClientResponse, summary="Get a client")
async def get_client(
    client_id: UUID,
    use_case: GetClientDep,
    user: CurrentUserDep,
) -> ClientResponse:
    return ClientResponse.from_view(await use_case.execute(client_id))


@router.patch("/{client_id}", response_model=ClientResponse, summary="Update client details")
async def update_client(
    client_id: UUID,
    payload: UpdateClientRequest,
    use_case: UpdateClientDep,
    user: ManagerDep,
) -> ClientResponse:
    view = await use_case.execute(
        UpdateClientDetailsCommand(
            client_id=client_id,
            name=payload.name,
            email=payload.email,
            notes=(payload.notes if "notes" in payload.model_fields_set else UNSET),
        )
    )
    return ClientResponse.from_view(view)


@router.post(
    "/{client_id}/suitability",
    response_model=SuitabilityResponse,
    summary="Re-assess the client's suitability profile",
)
async def assess_suitability(
    client_id: UUID,
    payload: AssessSuitabilityRequest,
    use_case: AssessSuitabilityDep,
    user: ManagerDep,
) -> SuitabilityResponse:
    view = await use_case.execute(
        AssessClientSuitabilityCommand(client_id=client_id, answers=payload.answers)
    )
    return SuitabilityResponse.from_view(view)


@router.post("/{client_id}/archive", response_model=ClientResponse, summary="Archive a client")
async def archive_client(
    client_id: UUID,
    use_case: ArchiveClientDep,
    user: ManagerDep,
) -> ClientResponse:
    return ClientResponse.from_view(await use_case.execute(client_id))


@router.post(
    "/{client_id}/reactivate", response_model=ClientResponse, summary="Reactivate a client"
)
async def reactivate_client(
    client_id: UUID,
    use_case: ReactivateClientDep,
    user: ManagerDep,
) -> ClientResponse:
    return ClientResponse.from_view(await use_case.execute(client_id))


__all__ = ["router"]
